"""
Credit Scoring Engine — Pan-African Microfinance SaaS
Computes configurable credit scores using internal data
(repayment history, loan cycles, group membership, mobile money activity)
and manual assessments (income stability, business tenure).
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional

from django.db.models import Avg, Count, Sum, Q, F
from django.utils import timezone

from apps.scoring.models import CreditScoreModel, ClientCreditScore
from apps.clients.models import Client
from apps.loans.models import Loan, Repayment


class CreditScoringEngine:
    """Compute credit scores for clients using tenant-configured models."""

    @classmethod
    def score_client(cls, tenant_id: str, client_id: str,
                     model_id: str = None, loan_id: str = None,
                     computed_for: str = 'MANUAL') -> ClientCreditScore:
        """
        Compute and store a credit score for a client.
        Uses the active scoring model for the tenant, or a specific model if provided.
        """
        client = Client.objects.get(id=client_id, tenant_id=tenant_id)

        if model_id:
            model = CreditScoreModel.objects.get(id=model_id, tenant_id=tenant_id)
        else:
            model = CreditScoreModel.objects.filter(
                tenant_id=tenant_id, is_active=True
            ).order_by('-model_version').first()

        if not model:
            raise ValueError('No active credit score model found for this tenant')

        # Compute each criterion
        component_scores = []
        total_weighted = Decimal('0')
        total_weight = Decimal('0')

        for criterion in model.criteria:
            code = criterion['code']
            weight = Decimal(str(criterion['weight']))
            source = criterion.get('source', 'internal')

            raw_value = cls._compute_criterion(client, code, source)
            # Normalise raw value to 0-100 scale
            normalised = cls._normalise(raw_value, code)
            weighted = (normalised * weight / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)

            component_scores.append({
                'code': code,
                'label': criterion.get('label', code),
                'weight': float(weight),
                'raw_value': float(raw_value) if raw_value is not None else None,
                'normalised_score': float(normalised),
                'weighted_score': float(weighted),
            })
            total_weighted += weighted
            total_weight += weight

        # Scale to 0-100
        if total_weight > 0:
            total_score = (total_weighted / total_weight * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            total_score = Decimal('0')

        # Determine risk label and recommendation from model's score ranges
        risk_label = 'HIGH_RISK'
        recommendation = 'DECLINE'
        for range_def in model.score_ranges:
            if range_def['min'] <= float(total_score) <= range_def['max']:
                risk_label = range_def['label']
                recommendation = range_def['recommendation']
                break

        # Store the score
        score = ClientCreditScore.objects.create(
            tenant_id=tenant_id,
            client=client,
            model=model,
            total_score=total_score,
            risk_label=risk_label,
            recommendation=recommendation,
            component_scores=component_scores,
            computed_for=computed_for,
            loan_id=loan_id,
        )

        return score

    @classmethod
    def _compute_criterion(cls, client: Client, code: str, source: str) -> Optional[Decimal]:
        """Compute raw value for a scoring criterion."""
        handlers = {
            'REPAYMENT_HISTORY': cls._score_repayment_history,
            'LOAN_CYCLE': cls._score_loan_cycles,
            'GROUP_MEMBERSHIP': cls._score_group_membership,
            'INCOME_STABILITY': cls._score_income_stability,
            'DEBT_TO_INCOME': cls._score_dti,
            'MOMO_ACTIVITY': cls._score_momo_activity,
            'BUSINESS_TENURE': cls._score_business_tenure,
        }
        handler = handlers.get(code)
        if handler:
            return handler(client)
        return None

    @classmethod
    def _score_repayment_history(cls, client: Client) -> Decimal:
        """Score based on past repayment performance (0-100)."""
        loans = Loan.objects.filter(
            client=client,
            tenant=client.tenant,
            status__in=['ACTIVE', 'DISBURSED', 'CLOSED']
        )
        if not loans.exists():
            return Decimal('50')  # No history = neutral

        total_schedules = 0
        on_time = 0
        for loan in loans:
            schedules = loan.schedule.filter(status='PAID')
            total_schedules += schedules.count()
            on_time += schedules.filter(days_late__lte=3).count()

        if total_schedules == 0:
            return Decimal('50')

        pct = Decimal(on_time) / Decimal(total_schedules) * Decimal('100')
        return pct.quantize(Decimal('0.01'))

    @classmethod
    def _score_loan_cycles(cls, client: Client) -> Decimal:
        """Score based on number of completed loan cycles."""
        completed = Loan.objects.filter(
            client=client, tenant=client.tenant, status='CLOSED'
        ).count()
        # 0 cycles = 20, 1 = 40, 2 = 60, 3 = 75, 4+ = 90
        scores = {0: 20, 1: 40, 2: 60, 3: 75}
        return Decimal(str(scores.get(completed, 90)))

    @classmethod
    def _score_group_membership(cls, client: Client) -> Decimal:
        """Score based on group membership tenure (months)."""
        membership = client.group_memberships.filter(is_active=True).first()
        if not membership:
            return Decimal('30')  # Not in a group
        months = (date.today() - membership.joined_at).days / 30
        if months >= 24:
            return Decimal('95')
        elif months >= 12:
            return Decimal('80')
        elif months >= 6:
            return Decimal('65')
        else:
            return Decimal('45')

    @classmethod
    def _score_income_stability(cls, client: Client) -> Decimal:
        """Score based on declared income and employment status."""
        if client.monthly_income and client.monthly_income > 0:
            if client.employer_name:
                return Decimal('80')  # Employed with income
            return Decimal('60')  # Self-declared income
        return Decimal('30')  # No income declared

    @classmethod
    def _score_dti(cls, client: Client) -> Decimal:
        """Score based on debt-to-income ratio (lower is better)."""
        if not client.monthly_income or client.monthly_income <= 0:
            return Decimal('40')  # Cannot compute

        # Calculate current monthly obligations
        active_loans = Loan.objects.filter(
            client=client, tenant=client.tenant,
            status__in=['ACTIVE', 'DISBURSED']
        )
        monthly_payments = Decimal('0')
        for loan in active_loans:
            next_schedule = loan.schedule.filter(
                status__in=['PENDING', 'OVERDUE']
            ).order_by('instalment_number').first()
            if next_schedule:
                monthly_payments += next_schedule.total_due

        dti = monthly_payments / client.monthly_income * Decimal('100')

        if dti <= 20:
            return Decimal('95')
        elif dti <= 35:
            return Decimal('80')
        elif dti <= 50:
            return Decimal('60')
        elif dti <= 70:
            return Decimal('35')
        else:
            return Decimal('15')

    @classmethod
    def _score_momo_activity(cls, client: Client) -> Decimal:
        """Score based on mobile money transaction volume (last 6 months)."""
        from apps.mobile_money.models import MobileMoneyTransaction
        six_months_ago = timezone.now() - timedelta(days=180)
        txn_count = MobileMoneyTransaction.objects.filter(
            client=client, tenant=client.tenant,
            status='SUCCESS',
            created_at__gte=six_months_ago,
        ).count()

        if txn_count >= 50:
            return Decimal('90')
        elif txn_count >= 20:
            return Decimal('75')
        elif txn_count >= 5:
            return Decimal('55')
        elif txn_count >= 1:
            return Decimal('40')
        return Decimal('25')  # No mobile money activity

    @classmethod
    def _score_business_tenure(cls, client: Client) -> Decimal:
        """Score based on how long client has been in business/employment."""
        # This relies on data that would be captured during onboarding
        # For now, use a proxy: how long they've been a client
        if client.created_at:
            months = (timezone.now() - client.created_at).days / 30
            if months >= 36:
                return Decimal('90')
            elif months >= 24:
                return Decimal('75')
            elif months >= 12:
                return Decimal('60')
            elif months >= 6:
                return Decimal('45')
        return Decimal('30')

    @staticmethod
    def _normalise(value: Optional[Decimal], code: str) -> Decimal:
        """Normalise raw value to 0-100 scale. Most handlers already return 0-100."""
        if value is None:
            return Decimal('50')  # Unknown = neutral
        return max(Decimal('0'), min(Decimal('100'), value))
