"""
Country Pack Configuration Engine
Loads regulatory rules (interest formulas, classification, provisioning)
per tenant and applies them to business operations.

This is the core of the multi-country architecture — the engine that makes
adding a new country a configuration task rather than a code change.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional
from functools import lru_cache

from django.core.cache import cache
from django.utils import timezone

from apps.tenants.models import Tenant, CountryPack, LicenceTier, RuleSetVersion, LicenceProfile


class CountryPackEngine:
    """
    Loads and caches country pack configuration for a tenant.
    All regulatory rule lookups flow through this engine.
    """

    CACHE_TTL = 3600  # 1 hour

    @classmethod
    def for_tenant(cls, tenant_id: str) -> 'CountryPackEngine':
        cache_key = f'country_pack_engine:{tenant_id}'
        engine = cache.get(cache_key)
        if engine is None:
            engine = cls(tenant_id)
            cache.set(cache_key, engine, cls.CACHE_TTL)
        return engine

    @classmethod
    def invalidate(cls, tenant_id: str):
        cache.delete(f'country_pack_engine:{tenant_id}')

    def __init__(self, tenant_id: str):
        self.tenant = Tenant.objects.select_related(
            'country', 'licence_tier', 'licence_profile'
        ).get(id=tenant_id)
        self.country_pack = self.tenant.country
        self.licence_tier = self.tenant.licence_tier
        self.licence_profile = self.tenant.licence_profile
        self.country_config = self.country_pack.config or {}

    # ─── FEATURE FLAGS ───

    @property
    def can_accept_deposits(self) -> bool:
        override = (self.licence_profile.permitted_features or {}).get('can_accept_deposits')
        if override is not None:
            return override
        return self.licence_tier.can_accept_deposits

    @property
    def can_offer_savings(self) -> bool:
        return self.licence_tier.can_offer_savings

    @property
    def is_credit_only(self) -> bool:
        return self.licence_tier.credit_only

    @property
    def can_do_transfers(self) -> bool:
        return self.licence_tier.can_do_transfers

    # ─── REGULATORY LIMITS ───

    @property
    def car_requirement(self) -> Optional[Decimal]:
        if self.licence_tier.car_requirement_pct:
            return self.licence_tier.car_requirement_pct
        return None

    @property
    def single_obligor_limit_pct(self) -> Optional[Decimal]:
        return self.licence_tier.single_obligor_limit_pct

    @property
    def insider_lending_limit_pct(self) -> Optional[Decimal]:
        return self.licence_tier.insider_lending_limit_pct

    @property
    def min_capital(self) -> Optional[Decimal]:
        return self.licence_tier.min_capital_amount

    @property
    def reporting_frequency(self) -> str:
        return self.licence_tier.reporting_frequency

    @property
    def aml_ctr_threshold(self) -> Optional[Decimal]:
        threshold = self.country_config.get('aml_ctr_threshold')
        return Decimal(str(threshold)) if threshold else None

    @property
    def national_id_format(self) -> str:
        return self.country_config.get('national_id_format', '')

    @property
    def national_id_name(self) -> str:
        return self.country_config.get('national_id_name', 'National ID')

    @property
    def phone_prefix(self) -> str:
        return self.country_config.get('phone_prefix', '')

    @property
    def audit_retention_years(self) -> int:
        return self.country_pack.audit_retention_years

    # ─── INTEREST CALCULATION ───

    def get_interest_formula(self, as_of_date: date = None) -> dict:
        """Get the active interest formula rule set for this tenant."""
        if self.licence_profile.active_interest_formula_id:
            rule = RuleSetVersion.objects.get(id=self.licence_profile.active_interest_formula_id)
            return rule.config

        # Fallback: find the latest active formula for this country
        as_of = as_of_date or date.today()
        rule = RuleSetVersion.objects.filter(
            country_code=self.country_pack.country_code,
            rule_type='INTEREST_FORMULA',
            effective_from__lte=as_of,
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=as_of)
        ).order_by('-effective_from', '-version_number').first()

        return rule.config if rule else {}

    def calculate_interest(self, principal: Decimal, annual_rate_pct: Decimal,
                          term_months: int, method: str = 'FLAT') -> dict:
        """
        Calculate interest based on the country's prescribed method.

        Returns: {
            'total_interest': Decimal,
            'total_repayable': Decimal,
            'periodic_payment': Decimal,
            'effective_annual_rate': Decimal,
        }
        """
        rate = annual_rate_pct / Decimal('100')

        if method == 'FLAT':
            total_interest = (principal * rate * Decimal(term_months) / Decimal('12')).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP)
            total_repayable = principal + total_interest
            periodic_payment = (total_repayable / Decimal(term_months)).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP)
            # Flat rate effective annual rate is higher than stated
            ear = self._flat_to_ear(rate, term_months)
        elif method == 'REDUCING_BALANCE':
            monthly_rate = rate / Decimal('12')
            if monthly_rate > 0:
                factor = (monthly_rate * (1 + monthly_rate) ** term_months) / \
                         ((1 + monthly_rate) ** term_months - 1)
                periodic_payment = (principal * factor).quantize(
                    Decimal('0.0001'), rounding=ROUND_HALF_UP)
            else:
                periodic_payment = (principal / Decimal(term_months)).quantize(
                    Decimal('0.0001'), rounding=ROUND_HALF_UP)
            total_repayable = periodic_payment * term_months
            total_interest = total_repayable - principal
            ear = annual_rate_pct
        else:
            raise ValueError(f'Unknown interest method: {method}')

        return {
            'total_interest': total_interest,
            'total_repayable': total_repayable,
            'periodic_payment': periodic_payment,
            'effective_annual_rate': ear,
        }

    @staticmethod
    def _flat_to_ear(flat_rate: Decimal, term_months: int) -> Decimal:
        """Convert flat rate to approximate effective annual rate."""
        n = term_months
        if n <= 0:
            return Decimal('0')
        ear = flat_rate * Decimal('2') * Decimal(n) / (Decimal(n) + 1)
        return (ear * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # ─── LOAN CLASSIFICATION ───

    def get_classification_rules(self, as_of_date: date = None) -> list:
        """Get active loan classification buckets for this tenant."""
        if self.licence_profile.active_classification_id:
            rule = RuleSetVersion.objects.get(id=self.licence_profile.active_classification_id)
            return rule.config.get('buckets', [])

        as_of = as_of_date or date.today()
        from django.db import models as db_models
        rule = RuleSetVersion.objects.filter(
            country_code=self.country_pack.country_code,
            rule_type='LOAN_CLASSIFICATION',
            effective_from__lte=as_of,
        ).filter(
            db_models.Q(effective_to__isnull=True) | db_models.Q(effective_to__gte=as_of)
        ).order_by('-effective_from', '-version_number').first()

        return rule.config.get('buckets', []) if rule else []

    def classify_loan(self, days_past_due: int, as_of_date: date = None) -> dict:
        """
        Classify a loan based on days past due using country-specific rules.

        Returns: {
            'classification': str,  # CURRENT, WATCH, SUBSTANDARD, DOUBTFUL, LOSS
            'provision_pct': Decimal,
        }
        """
        buckets = self.get_classification_rules(as_of_date)
        if not buckets:
            # Fallback: standard microfinance classification
            buckets = [
                {'classification': 'CURRENT', 'min_dpd': 0, 'max_dpd': 0, 'provision_pct': 1},
                {'classification': 'WATCH', 'min_dpd': 1, 'max_dpd': 30, 'provision_pct': 5},
                {'classification': 'SUBSTANDARD', 'min_dpd': 31, 'max_dpd': 90, 'provision_pct': 25},
                {'classification': 'DOUBTFUL', 'min_dpd': 91, 'max_dpd': 180, 'provision_pct': 50},
                {'classification': 'LOSS', 'min_dpd': 181, 'max_dpd': None, 'provision_pct': 100},
            ]

        for bucket in buckets:
            min_dpd = bucket.get('min_dpd', 0)
            max_dpd = bucket.get('max_dpd')
            if days_past_due >= min_dpd and (max_dpd is None or days_past_due <= max_dpd):
                return {
                    'classification': bucket['classification'],
                    'provision_pct': Decimal(str(bucket['provision_pct'])),
                }

        # If nothing matches, default to LOSS
        return {'classification': 'LOSS', 'provision_pct': Decimal('100')}

    def calculate_provision(self, outstanding_principal: Decimal, days_past_due: int,
                           as_of_date: date = None) -> dict:
        """
        Calculate required provision for a loan.

        Returns: {
            'classification': str,
            'provision_pct': Decimal,
            'provision_amount': Decimal,
        }
        """
        result = self.classify_loan(days_past_due, as_of_date)
        provision_amount = (outstanding_principal * result['provision_pct'] / Decimal('100')).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP)
        return {
            **result,
            'provision_amount': provision_amount,
        }

    # ─── LIMIT CHECKS ───

    def check_single_obligor_limit(self, client_total_exposure: Decimal,
                                    institution_capital: Decimal) -> dict:
        """Check if a client's total exposure breaches the single obligor limit."""
        limit_pct = self.single_obligor_limit_pct
        if not limit_pct or not institution_capital:
            return {'breached': False, 'limit_pct': None, 'exposure_pct': None}

        exposure_pct = (client_total_exposure / institution_capital * Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        breached = exposure_pct > limit_pct
        return {
            'breached': breached,
            'limit_pct': limit_pct,
            'exposure_pct': exposure_pct,
            'headroom': limit_pct - exposure_pct,
        }

    def check_insider_lending_limit(self, total_insider_exposure: Decimal,
                                     institution_capital: Decimal) -> dict:
        """Check aggregate insider lending exposure."""
        limit_pct = self.insider_lending_limit_pct
        if not limit_pct or not institution_capital:
            return {'breached': False, 'limit_pct': None, 'exposure_pct': None}

        exposure_pct = (total_insider_exposure / institution_capital * Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        breached = exposure_pct > limit_pct
        return {
            'breached': breached,
            'limit_pct': limit_pct,
            'exposure_pct': exposure_pct,
        }

    # ─── NATIONAL ID VALIDATION ───

    def validate_national_id(self, id_number: str) -> dict:
        """Validate national ID format for this country."""
        import re
        pattern = self.country_config.get('national_id_format', '')
        if not pattern:
            return {'valid': True, 'message': 'No format validation configured'}

        # Convert format pattern to regex
        regex = pattern.replace('X', r'\d').replace('-', r'\-')
        regex = f'^{regex}$'

        if re.match(regex, id_number):
            return {'valid': True, 'message': 'Valid format'}
        else:
            return {
                'valid': False,
                'message': f'Invalid {self.national_id_name} format. Expected: {pattern}'
            }

    # ─── AML THRESHOLD CHECK ───

    def check_aml_threshold(self, transaction_amount: Decimal) -> dict:
        """Check if a transaction exceeds the AML reporting threshold."""
        threshold = self.aml_ctr_threshold
        if not threshold:
            return {'exceeds_threshold': False, 'threshold': None}

        exceeds = transaction_amount >= threshold
        return {
            'exceeds_threshold': exceeds,
            'threshold': threshold,
            'threshold_currency': self.country_config.get('aml_ctr_threshold_currency', ''),
            'report_type': 'CTR' if exceeds else None,
        }


class LoanClassificationService:
    """
    Batch service to reclassify all active loans for a tenant.
    Run nightly via Celery beat.
    """

    @classmethod
    def reclassify_tenant(cls, tenant_id: str):
        """Reclassify all active loans for a tenant based on current DPD."""
        from apps.loans.models import Loan
        engine = CountryPackEngine.for_tenant(tenant_id)
        today = date.today()

        loans = Loan.objects.filter(
            tenant_id=tenant_id,
            status__in=['ACTIVE', 'DISBURSED']
        )

        updated = 0
        for loan in loans.iterator(chunk_size=200):
            # Calculate days past due from most overdue schedule
            overdue = loan.schedule.filter(
                status__in=['PENDING', 'PARTIAL', 'OVERDUE'],
                due_date__lt=today
            ).order_by('due_date').first()

            if overdue:
                dpd = (today - overdue.due_date).days
            else:
                dpd = 0

            result = engine.calculate_provision(loan.outstanding_principal, dpd, today)

            changed = False
            if loan.days_past_due != dpd:
                loan.days_past_due = dpd
                changed = True
            if loan.classification != result['classification']:
                loan.classification = result['classification']
                changed = True
            if loan.provision_rate_pct != result['provision_pct']:
                loan.provision_rate_pct = result['provision_pct']
                changed = True
            if loan.provision_amount != result['provision_amount']:
                loan.provision_amount = result['provision_amount']
                changed = True

            # Update arrears
            from django.db.models import Sum, F
            arrears = loan.schedule.filter(
                status__in=['PENDING', 'PARTIAL', 'OVERDUE'],
                due_date__lt=today
            ).aggregate(
                total_arrears=Sum(F('total_due') - F('total_paid'))
            )
            arrears_amt = arrears['total_arrears'] or Decimal('0')
            if loan.arrears_amount != arrears_amt:
                loan.arrears_amount = arrears_amt
                changed = True

            # Mark overdue schedules
            loan.schedule.filter(
                status__in=['PENDING', 'PARTIAL'],
                due_date__lt=today
            ).update(status='OVERDUE')

            if changed:
                loan.save(update_fields=[
                    'days_past_due', 'classification', 'provision_rate_pct',
                    'provision_amount', 'arrears_amount', 'updated_at'
                ])
                updated += 1

        return {'tenant_id': tenant_id, 'loans_processed': loans.count(), 'loans_updated': updated}

    @classmethod
    def reclassify_all_tenants(cls):
        """Reclassify loans across all active tenants."""
        results = []
        for tenant_id in Tenant.objects.filter(
            status='ACTIVE', subscription_active=True
        ).values_list('id', flat=True):
            result = cls.reclassify_tenant(str(tenant_id))
            results.append(result)
        return results
