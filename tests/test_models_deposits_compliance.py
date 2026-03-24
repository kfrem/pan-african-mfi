"""
Tests for Deposit, Compliance, GL, Investor, and MobileMoney models.
Validates every field and financial constraint.
"""
from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.deposits.models import DepositProduct, DepositAccount, DepositTransaction
from apps.compliance.models import AmlAlert, Str, TransactionMonitoringRule, PrudentialReturn
from apps.ledger.models import GlAccount, GlTransaction, GlEntry, AccountingPeriod, ExchangeRate
from apps.investors.models import InvestorProfile, Dividend, InvestorShareLink
from apps.mobile_money.models import MobileMoneyProvider, MobileMoneyTransaction, MobileMoneyReconciliation


pytestmark = pytest.mark.models


# ─── DEPOSITS ─────────────────────────────────────────────────────────────────

class TestDepositProduct:
    """DepositProduct — savings, fixed deposit, current account products."""

    def test_savings_product_all_fields(self, savings_product, tenant):
        p = savings_product
        assert p.tenant == tenant
        assert p.product_code == 'SAV-001'
        assert p.product_name == 'Standard Savings'
        assert p.product_type == 'SAVINGS'
        assert p.interest_rate_pct == Decimal('5.0000')
        assert p.min_balance == Decimal('20.00')
        assert p.notice_period_days == 0
        assert p.is_active is True

    def test_fixed_deposit_product(self, fixed_deposit_product):
        assert fixed_deposit_product.product_type == 'FIXED_DEPOSIT'
        assert fixed_deposit_product.interest_rate_pct == Decimal('12.0000')
        assert fixed_deposit_product.notice_period_days == 30

    def test_product_type_choices(self, tenant, db):
        for ptype in ['SAVINGS', 'FIXED_DEPOSIT', 'CURRENT']:
            p = DepositProduct.objects.create(
                tenant=tenant,
                product_code=f'DEP-{ptype}',
                product_name=f'{ptype} Product',
                product_type=ptype,
            )
            assert p.product_type == ptype

    def test_unique_product_code_per_tenant(self, savings_product, tenant, db):
        with pytest.raises(IntegrityError):
            DepositProduct.objects.create(
                tenant=tenant,
                product_code='SAV-001',
                product_name='Duplicate Savings',
                product_type='SAVINGS',
            )

    def test_str_representation(self, savings_product):
        result = str(savings_product)
        assert 'Standard Savings' in result


class TestDepositAccount:
    """DepositAccount — client savings/deposit account."""

    def test_all_fields(self, deposit_account, tenant, verified_client, savings_product):
        a = deposit_account
        assert a.tenant == tenant
        assert a.client == verified_client
        assert a.product == savings_product
        assert a.account_number == 'SAV-2024-00001'
        assert a.currency == 'GHS'
        assert a.balance == Decimal('500.00')
        assert a.status == 'ACTIVE'
        assert a.opened_at is not None
        assert a.closed_at is None
        assert a.maturity_date is None

    def test_fixed_deposit_has_maturity_date(self, fixed_deposit_account):
        assert fixed_deposit_account.maturity_date is not None
        assert fixed_deposit_account.maturity_date > date.today()

    def test_status_choices(self, tenant, verified_client, savings_product, db):
        for i, status in enumerate(['ACTIVE', 'DORMANT', 'CLOSED']):
            a = DepositAccount.objects.create(
                tenant=tenant,
                client=verified_client,
                product=savings_product,
                account_number=f'SAV-STATUS-{i:05d}',
                currency='GHS',
                balance=Decimal('100.00'),
                status=status,
                opened_at=date.today(),
            )
            assert a.status == status

    def test_unique_account_number_per_tenant(self, deposit_account, tenant, verified_client, savings_product, db):
        with pytest.raises(IntegrityError):
            DepositAccount.objects.create(
                tenant=tenant,
                client=verified_client,
                product=savings_product,
                account_number='SAV-2024-00001',
                currency='GHS',
                balance=Decimal('0.00'),
                status='ACTIVE',
                opened_at=date.today(),
            )

    def test_balance_precision(self, deposit_account):
        assert isinstance(deposit_account.balance, Decimal)
        # Balance should have 4 decimal precision
        assert deposit_account.balance == Decimal('500.0000')

    def test_closed_account(self, deposit_account, db):
        deposit_account.status = 'CLOSED'
        deposit_account.closed_at = date.today()
        deposit_account.balance = Decimal('0.00')
        deposit_account.save()
        deposit_account.refresh_from_db()
        assert deposit_account.status == 'CLOSED'
        assert deposit_account.closed_at == date.today()


class TestDepositTransaction:
    """DepositTransaction — transaction history on deposit accounts."""

    def test_creation(self, tenant, deposit_account, loan_officer_user, db):
        txn = DepositTransaction.objects.create(
            tenant=tenant,
            account=deposit_account,
            transaction_type='DEPOSIT',
            amount=Decimal('200.00'),
            balance_after=Decimal('700.00'),
            description='Cash deposit at counter',
            payment_method='CASH',
            reference='DEP-REF-001',
            performed_by=loan_officer_user,
        )
        assert txn.transaction_type == 'DEPOSIT'
        assert txn.amount == Decimal('200.00')
        assert txn.balance_after == Decimal('700.00')

    def test_transaction_type_choices(self, tenant, deposit_account, loan_officer_user, db):
        types = ['DEPOSIT', 'WITHDRAWAL', 'INTEREST_CREDIT', 'FEE_DEBIT', 'TRANSFER']
        for i, ttype in enumerate(types):
            txn = DepositTransaction.objects.create(
                tenant=tenant,
                account=deposit_account,
                transaction_type=ttype,
                amount=Decimal('10.00'),
                balance_after=Decimal('490.00'),
                performed_by=loan_officer_user,
            )
            assert txn.transaction_type == ttype

    def test_sync_fields(self, tenant, deposit_account, loan_officer_user, db):
        txn = DepositTransaction.objects.create(
            tenant=tenant,
            account=deposit_account,
            transaction_type='WITHDRAWAL',
            amount=Decimal('50.00'),
            balance_after=Decimal('450.00'),
            performed_by=loan_officer_user,
            device_id='mobile-device-001',
            sync_status='PENDING_UPLOAD',
        )
        assert txn.device_id == 'mobile-device-001'
        assert txn.sync_id is not None

    def test_interest_credit_positive(self, tenant, deposit_account, loan_officer_user, db):
        txn = DepositTransaction.objects.create(
            tenant=tenant,
            account=deposit_account,
            transaction_type='INTEREST_CREDIT',
            amount=Decimal('25.00'),
            balance_after=Decimal('525.00'),
            description='Monthly interest credit',
            performed_by=loan_officer_user,
        )
        assert txn.amount > Decimal('0')


# ─── COMPLIANCE ───────────────────────────────────────────────────────────────

class TestAmlAlert:
    """AmlAlert — system-generated AML monitoring alerts."""

    def test_all_fields(self, aml_alert, tenant, individual_client, compliance_user):
        a = aml_alert
        assert a.tenant == tenant
        assert a.client == individual_client
        assert a.alert_type == 'THRESHOLD'
        assert a.trigger_description != ''
        assert a.trigger_amount == Decimal('12000.00')
        assert a.trigger_currency == 'GHS'
        assert a.status == 'OPEN'
        assert a.assigned_to == compliance_user
        assert a.risk_score == 75
        assert a.created_at is not None

    def test_status_choices(self, tenant, individual_client, db):
        statuses = ['OPEN', 'UNDER_REVIEW', 'ESCALATED', 'STR_FILED', 'CLOSED_NO_ACTION']
        for status in statuses:
            alert = AmlAlert.objects.create(
                tenant=tenant,
                client=individual_client,
                alert_type='THRESHOLD',
                trigger_description='Test alert',
                status=status,
            )
            assert alert.status == status

    def test_risk_score_range(self, aml_alert, db):
        """Risk score must be between 1 and 100."""
        assert 1 <= aml_alert.risk_score <= 100

    def test_escalation_tracking(self, aml_alert, db):
        aml_alert.status = 'ESCALATED'
        aml_alert.escalated_at = timezone.now()
        aml_alert.save()
        aml_alert.refresh_from_db()
        assert aml_alert.status == 'ESCALATED'
        assert aml_alert.escalated_at is not None

    def test_closure_tracking(self, aml_alert, compliance_user, db):
        aml_alert.status = 'CLOSED_NO_ACTION'
        aml_alert.closed_at = timezone.now()
        aml_alert.closed_by = compliance_user
        aml_alert.review_notes = 'Reviewed — legitimate business transaction.'
        aml_alert.save()
        assert aml_alert.closed_by == compliance_user
        assert 'legitimate' in aml_alert.review_notes.lower()

    def test_trigger_amount_nullable(self, tenant, individual_client, db):
        alert = AmlAlert.objects.create(
            tenant=tenant,
            client=individual_client,
            alert_type='PATTERN',
            trigger_description='Unusual transaction pattern detected',
            trigger_amount=None,
        )
        assert alert.trigger_amount is None


class TestStr:
    """STR/CTR — Suspicious Transaction Report filing."""

    def test_str_creation(self, tenant, individual_client, compliance_user, aml_alert, db):
        report = Str.objects.create(
            tenant=tenant,
            alert=aml_alert,
            client=individual_client,
            report_type='STR',
            narrative='Client made multiple cash deposits just below GHS 10,000 threshold over 3 days.',
            transaction_amount=Decimal('28500.00'),
            transaction_currency='GHS',
            transaction_date=date.today() - timedelta(days=7),
            status='DRAFT',
            filed_by=compliance_user,
            deadline=date.today() + timedelta(days=3),
        )
        assert report.report_type == 'STR'
        assert report.status == 'DRAFT'
        assert report.narrative != ''
        assert report.deadline is not None

    def test_ctr_creation(self, tenant, individual_client, compliance_user, db):
        report = Str.objects.create(
            tenant=tenant,
            client=individual_client,
            report_type='CTR',
            narrative='Cash transaction exceeds CTR threshold.',
            transaction_amount=Decimal('15000.00'),
            transaction_currency='GHS',
            transaction_date=date.today(),
            status='DRAFT',
            filed_by=compliance_user,
        )
        assert report.report_type == 'CTR'

    def test_status_choices(self, tenant, individual_client, compliance_user, db):
        for status in ['DRAFT', 'SUBMITTED', 'ACKNOWLEDGED', 'REJECTED_BY_FIC']:
            report = Str.objects.create(
                tenant=tenant,
                client=individual_client,
                report_type='STR',
                narrative=f'Test {status} narrative.',
                status=status,
                filed_by=compliance_user,
            )
            assert report.status == status

    def test_submission_tracking(self, tenant, individual_client, compliance_user, manager_user, db):
        report = Str.objects.create(
            tenant=tenant,
            client=individual_client,
            report_type='STR',
            narrative='Suspicious activity report.',
            status='SUBMITTED',
            filed_by=compliance_user,
            approved_by=manager_user,
            submitted_to='Financial Intelligence Centre',
            submitted_at=timezone.now(),
            fic_reference='FIC-2024-01234',
        )
        assert report.fic_reference == 'FIC-2024-01234'
        assert report.approved_by == manager_user


class TestTransactionMonitoringRule:
    """TransactionMonitoringRule — AML rules per country."""

    def test_all_fields(self, monitoring_rule, country_gh):
        r = monitoring_rule
        assert r.country == country_gh
        assert r.rule_code == 'GH-THRESH-001'
        assert r.rule_name == 'Single Transaction Threshold'
        assert r.rule_type == 'THRESHOLD'
        assert isinstance(r.config, dict)
        assert r.severity == 'HIGH'
        assert r.is_active is True

    def test_rule_type_choices(self, country_gh, db):
        for rtype in ['THRESHOLD', 'PATTERN', 'VELOCITY']:
            rule = TransactionMonitoringRule.objects.create(
                country=country_gh,
                rule_code=f'GH-{rtype}-001',
                rule_name=f'{rtype} Rule',
                rule_type=rtype,
                config={},
                severity='MEDIUM',
            )
            assert rule.rule_type == rtype

    def test_severity_choices(self, country_gh, db):
        for severity in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            rule = TransactionMonitoringRule.objects.create(
                country=country_gh,
                rule_code=f'GH-SEV-{severity}',
                rule_name=f'{severity} Severity Rule',
                rule_type='THRESHOLD',
                config={'threshold': 1000},
                severity=severity,
            )
            assert rule.severity == severity

    def test_config_json_structure(self, monitoring_rule):
        assert 'threshold_amount' in monitoring_rule.config
        assert monitoring_rule.config['threshold_amount'] == 10000


class TestPrudentialReturn:
    """PrudentialReturn — regulatory returns generation and submission."""

    def test_all_fields(self, prudential_return, tenant, compliance_user):
        r = prudential_return
        assert r.tenant == tenant
        assert r.return_template_code == 'BOG-MFI-MONTHLY'
        assert r.return_name == 'Monthly MFI Return'
        assert r.reporting_period == '2024-01'
        assert r.due_date == date(2024, 2, 15)
        assert r.status == 'PENDING'
        assert r.generated_by == compliance_user

    def test_status_choices(self, tenant, compliance_user, db):
        for status in ['PENDING', 'GENERATED', 'REVIEWED', 'SUBMITTED', 'OVERDUE']:
            r = PrudentialReturn.objects.create(
                tenant=tenant,
                return_template_code='BOG-TEST',
                return_name='Test Return',
                reporting_period=f'2024-{status[:2]}',
                due_date=date(2024, 3, 15),
                status=status,
            )
            assert r.status == status

    def test_variance_tracking(self, prudential_return, db):
        prudential_return.system_computed_values = {'par30_pct': 4.5, 'car_pct': 12.3}
        prudential_return.submitted_values = {'par30_pct': 4.2, 'car_pct': 12.5}
        prudential_return.variance_pct = Decimal('1.50')
        prudential_return.save()
        prudential_return.refresh_from_db()
        assert prudential_return.variance_pct == Decimal('1.50')

    def test_submission_fields(self, prudential_return, compliance_user, db):
        prudential_return.status = 'SUBMITTED'
        prudential_return.submitted_by = compliance_user
        prudential_return.submitted_at = timezone.now()
        prudential_return.save()
        assert prudential_return.submitted_by == compliance_user
        assert prudential_return.submitted_at is not None


# ─── GL / LEDGER ──────────────────────────────────────────────────────────────

class TestGlAccount:
    """GlAccount — chart of accounts for double-entry bookkeeping."""

    def test_asset_account(self, gl_cash_account, tenant):
        a = gl_cash_account
        assert a.tenant == tenant
        assert a.account_code == '1001'
        assert a.account_name == 'Cash in Vault'
        assert a.account_type == 'ASSET'
        assert a.normal_balance == 'D'
        assert a.is_header is False
        assert a.is_system_account is True
        assert a.is_active is True

    def test_income_account_credit_normal(self, gl_interest_income):
        assert gl_interest_income.account_type == 'INCOME'
        assert gl_interest_income.normal_balance == 'C'

    def test_account_type_choices(self, tenant, db):
        for atype in ['ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE']:
            a = GlAccount.objects.create(
                tenant=tenant,
                account_code=f'TEST-{atype}',
                account_name=f'{atype} Account',
                account_type=atype,
                normal_balance='D' if atype in ('ASSET', 'EXPENSE') else 'C',
                currency='GHS',
            )
            assert a.account_type == atype

    def test_normal_balance_choices(self, tenant, db):
        for nb in ['D', 'C']:
            a = GlAccount.objects.create(
                tenant=tenant,
                account_code=f'TEST-NB-{nb}',
                account_name=f'Normal Balance {nb}',
                account_type='ASSET',
                normal_balance=nb,
                currency='GHS',
            )
            assert a.normal_balance == nb

    def test_unique_account_code_per_tenant(self, gl_cash_account, tenant, db):
        with pytest.raises(IntegrityError):
            GlAccount.objects.create(
                tenant=tenant,
                account_code='1001',
                account_name='Duplicate Cash',
                account_type='ASSET',
                normal_balance='D',
                currency='GHS',
            )

    def test_parent_account_hierarchy(self, gl_cash_account, tenant, db):
        """Sub-account can reference a header parent account."""
        header = GlAccount.objects.create(
            tenant=tenant,
            account_code='1000',
            account_name='Current Assets (Header)',
            account_type='ASSET',
            normal_balance='D',
            is_header=True,
            currency='GHS',
        )
        gl_cash_account.parent_account = header
        gl_cash_account.save()
        assert gl_cash_account.parent_account == header

    def test_regulatory_mapping_code(self, tenant, db):
        a = GlAccount.objects.create(
            tenant=tenant,
            account_code='2100',
            account_name='Gross Loans Outstanding',
            account_type='ASSET',
            normal_balance='D',
            currency='GHS',
            regulatory_mapping_code='BOG_LOANS_GROSS',
        )
        assert a.regulatory_mapping_code == 'BOG_LOANS_GROSS'

    def test_str_representation(self, gl_cash_account):
        result = str(gl_cash_account)
        assert '1001' in result
        assert 'Cash' in result


class TestAccountingPeriod:
    """AccountingPeriod — open/close control for monthly periods."""

    def test_all_fields(self, accounting_period, tenant):
        p = accounting_period
        assert p.tenant == tenant
        assert p.period_name == 'January 2024'
        assert p.start_date == date(2024, 1, 1)
        assert p.end_date == date(2024, 1, 31)
        assert p.status == 'OPEN'

    def test_status_choices(self, tenant, db):
        for i, status in enumerate(['OPEN', 'CLOSING', 'CLOSED']):
            p = AccountingPeriod.objects.create(
                tenant=tenant,
                period_name=f'Test Period {i}',
                start_date=date(2024, i + 1, 1),
                end_date=date(2024, i + 1, 28),
                status=status,
            )
            assert p.status == status

    def test_unique_period_name_per_tenant(self, accounting_period, tenant, db):
        with pytest.raises(IntegrityError):
            AccountingPeriod.objects.create(
                tenant=tenant,
                period_name='January 2024',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

    def test_closed_period_sets_closed_by(self, accounting_period, compliance_user, db):
        accounting_period.status = 'CLOSED'
        accounting_period.closed_by = compliance_user
        accounting_period.closed_at = timezone.now()
        accounting_period.save()
        assert accounting_period.closed_by == compliance_user


class TestGlTransaction:
    """GlTransaction — double-entry transaction header."""

    def test_creation(self, tenant, accounting_period, loan_officer_user, db):
        txn = GlTransaction.objects.create(
            tenant=tenant,
            transaction_ref='GL-2024-000001',
            transaction_date=date(2024, 1, 15),
            period=accounting_period,
            description='Loan disbursement - LN-202401-00001',
            source_type='LOAN_DISBURSEMENT',
            source_id=uuid.uuid4(),
            posted_by=loan_officer_user,
            is_reversal=False,
        )
        assert txn.transaction_ref == 'GL-2024-000001'
        assert txn.source_type == 'LOAN_DISBURSEMENT'
        assert txn.is_reversal is False

    def test_source_type_choices(self, tenant, accounting_period, loan_officer_user, db):
        types = ['LOAN_DISBURSEMENT', 'REPAYMENT', 'DEPOSIT', 'MANUAL',
                 'FEE', 'PROVISION', 'INTEREST_ACCRUAL', 'MOBILE_MONEY']
        for i, stype in enumerate(types):
            txn = GlTransaction.objects.create(
                tenant=tenant,
                transaction_ref=f'GL-TYPE-{i:06d}',
                transaction_date=date.today(),
                period=accounting_period,
                posted_by=loan_officer_user,
                source_type=stype,
            )
            assert txn.source_type == stype


class TestGlEntry:
    """GlEntry — debit/credit lines within a GL transaction."""

    def test_double_entry_creation(self, tenant, accounting_period, loan_officer_user,
                                    gl_cash_account, gl_loan_account, db):
        txn = GlTransaction.objects.create(
            tenant=tenant,
            transaction_ref='GL-2024-000001',
            transaction_date=date.today(),
            period=accounting_period,
            posted_by=loan_officer_user,
            source_type='LOAN_DISBURSEMENT',
        )
        # Debit loans receivable
        debit = GlEntry.objects.create(
            tenant=tenant,
            transaction=txn,
            account=gl_loan_account,
            debit_amount=Decimal('5000.00'),
            credit_amount=Decimal('0.00'),
            currency='GHS',
            description='Loan disbursed',
        )
        # Credit cash
        credit = GlEntry.objects.create(
            tenant=tenant,
            transaction=txn,
            account=gl_cash_account,
            debit_amount=Decimal('0.00'),
            credit_amount=Decimal('5000.00'),
            currency='GHS',
            description='Cash disbursed',
        )
        assert debit.debit_amount == Decimal('5000.00')
        assert credit.credit_amount == Decimal('5000.00')
        # Double entry must balance
        total_debits = txn.entries.aggregate(
            total=__import__('django.db.models', fromlist=['Sum']).Sum('debit_amount')
        )['total']
        total_credits = txn.entries.aggregate(
            total=__import__('django.db.models', fromlist=['Sum']).Sum('credit_amount')
        )['total']
        assert total_debits == total_credits


class TestExchangeRate:
    """ExchangeRate — daily FX rates for multi-currency support."""

    def test_creation(self, db):
        rate = ExchangeRate.objects.create(
            base_currency='USD',
            target_currency='GHS',
            rate=Decimal('12.50000000'),
            rate_date=date.today(),
            source='Reuters',
        )
        assert rate.base_currency == 'USD'
        assert rate.target_currency == 'GHS'
        assert rate.rate == Decimal('12.50000000')

    def test_unique_rate_per_day(self, db):
        ExchangeRate.objects.create(
            base_currency='USD',
            target_currency='GHS',
            rate=Decimal('12.50000000'),
            rate_date=date(2024, 1, 15),
        )
        with pytest.raises(IntegrityError):
            ExchangeRate.objects.create(
                base_currency='USD',
                target_currency='GHS',
                rate=Decimal('12.55000000'),
                rate_date=date(2024, 1, 15),
            )

    def test_8_decimal_precision(self, db):
        rate = ExchangeRate.objects.create(
            base_currency='EUR',
            target_currency='GHS',
            rate=Decimal('13.48620000'),
            rate_date=date.today(),
        )
        assert rate.rate == Decimal('13.48620000')


# ─── INVESTORS ────────────────────────────────────────────────────────────────

class TestInvestorProfile:
    """InvestorProfile — funder/investor records."""

    def test_all_fields(self, investor_profile, tenant, manager_user):
        p = investor_profile
        assert p.tenant == tenant
        assert p.user == manager_user
        assert p.investor_name == 'AfricaGrowth Fund'
        assert p.investor_type == 'FUND'
        assert p.investment_currency == 'USD'
        assert p.invested_amount == Decimal('500000.00')
        assert p.investment_date == date(2024, 1, 1)
        assert p.exchange_rate_at_investment == Decimal('12.50000000')
        assert p.status == 'ACTIVE'
        assert isinstance(p.covenant_thresholds, dict)

    def test_investor_type_choices(self, tenant, manager_user, db):
        for itype in ['INDIVIDUAL', 'INSTITUTIONAL', 'FUND']:
            p = InvestorProfile.objects.create(
                tenant=tenant,
                user=manager_user,
                investor_name=f'{itype} Investor',
                investor_type=itype,
                investment_currency='GHS',
                invested_amount=Decimal('100000.00'),
                invested_amount_local=Decimal('100000.00'),
                investment_date=date.today(),
                exchange_rate_at_investment=Decimal('1.00000000'),
            )
            assert p.investor_type == itype

    def test_covenant_thresholds_json(self, investor_profile):
        thresholds = investor_profile.covenant_thresholds
        assert 'par30_max_pct' in thresholds
        assert 'car_min_pct' in thresholds

    def test_status_choices(self, tenant, manager_user, db):
        for status in ['ACTIVE', 'SUSPENDED', 'EXITED']:
            p = InvestorProfile.objects.create(
                tenant=tenant,
                user=manager_user,
                investor_name=f'{status} Investor',
                investor_type='FUND',
                investment_currency='USD',
                invested_amount=Decimal('100000.00'),
                invested_amount_local=Decimal('1250000.00'),
                investment_date=date.today(),
                exchange_rate_at_investment=Decimal('12.50000000'),
                status=status,
            )
            assert p.status == status


class TestDividend:
    """Dividend — declarations and payments to investors."""

    def test_creation(self, tenant, investor_profile, manager_user, db):
        div = Dividend.objects.create(
            tenant=tenant,
            investor=investor_profile,
            period='Q1-2024',
            declared_rate_pct=Decimal('5.0000'),
            amount=Decimal('25000.00'),
            currency='USD',
            status='DECLARED',
        )
        assert div.period == 'Q1-2024'
        assert div.declared_rate_pct == Decimal('5.0000')
        assert div.status == 'DECLARED'

    def test_dividend_status_choices(self, tenant, investor_profile, manager_user, db):
        for status in ['DECLARED', 'APPROVED', 'PAID', 'REINVESTED']:
            div = Dividend.objects.create(
                tenant=tenant,
                investor=investor_profile,
                period=f'{status}-2024',
                declared_rate_pct=Decimal('5.00'),
                amount=Decimal('10000.00'),
                currency='USD',
                status=status,
            )
            assert div.status == status


class TestInvestorShareLink:
    """InvestorShareLink — token-gated investor dashboard links."""

    def test_creation(self, tenant, investor_profile, manager_user, db):
        link = InvestorShareLink.objects.create(
            tenant=tenant,
            investor_profile=investor_profile,
            token='tok_abc123def456ghi789',
            password_hash='',
            expires_at=timezone.now() + timedelta(days=30),
            max_views=10,
            view_count=0,
            created_by=manager_user,
            is_active=True,
        )
        assert link.token == 'tok_abc123def456ghi789'
        assert link.is_active is True
        assert link.view_count == 0

    def test_token_uniqueness(self, tenant, investor_profile, manager_user, db):
        InvestorShareLink.objects.create(
            tenant=tenant,
            investor_profile=investor_profile,
            token='tok_unique_001',
            created_by=manager_user,
        )
        with pytest.raises(IntegrityError):
            InvestorShareLink.objects.create(
                tenant=tenant,
                investor_profile=investor_profile,
                token='tok_unique_001',
                created_by=manager_user,
            )

    def test_view_count_increments(self, tenant, investor_profile, manager_user, db):
        link = InvestorShareLink.objects.create(
            tenant=tenant,
            investor_profile=investor_profile,
            token='tok_views_test',
            created_by=manager_user,
            max_views=5,
        )
        link.view_count += 1
        link.save()
        assert link.view_count == 1


# ─── MOBILE MONEY ─────────────────────────────────────────────────────────────

class TestMobileMoneyProvider:
    """MobileMoneyProvider — per-country MoMo provider config."""

    def test_all_fields(self, mtn_provider, country_gh, gl_cash_account):
        p = mtn_provider
        assert p.country == country_gh
        assert p.provider_code == 'MTN_GH'
        assert p.provider_name == 'MTN Mobile Money'
        assert p.api_type == 'AFRICAS_TALKING'
        assert p.currency == 'GHS'
        assert p.phone_prefix == '024'
        assert p.phone_regex != ''
        assert p.min_transaction == Decimal('1.00')
        assert p.max_transaction == Decimal('10000.00')
        assert p.is_active is True
        assert p.settlement_gl_account == gl_cash_account

    def test_api_type_choices(self, country_gh, gl_cash_account, db):
        for i, api_type in enumerate(['AFRICAS_TALKING', 'DIRECT_API', 'MANUAL']):
            p = MobileMoneyProvider.objects.create(
                country=country_gh,
                provider_code=f'PROVIDER_{api_type}',
                provider_name=f'{api_type} Provider',
                api_type=api_type,
                currency='GHS',
                settlement_gl_account=gl_cash_account,
            )
            assert p.api_type == api_type

    def test_unique_country_provider_code(self, mtn_provider, country_gh, gl_cash_account, db):
        with pytest.raises(IntegrityError):
            MobileMoneyProvider.objects.create(
                country=country_gh,
                provider_code='MTN_GH',
                provider_name='Duplicate MTN',
                api_type='MANUAL',
                currency='GHS',
            )

    def test_fee_structure_json(self, mtn_provider):
        assert isinstance(mtn_provider.fee_structure, dict)
        assert 'percentage' in mtn_provider.fee_structure


class TestMobileMoneyTransaction:
    """MobileMoneyTransaction — collection/disbursement records."""

    def test_creation(self, tenant, mtn_provider, verified_client, disbursed_loan, loan_officer_user, db):
        txn = MobileMoneyTransaction.objects.create(
            tenant=tenant,
            provider=mtn_provider,
            transaction_type='COLLECTION',
            direction='IN',
            phone_number='+233244100001',
            amount=Decimal('566.67'),
            currency='GHS',
            fee_amount=Decimal('5.67'),
            fee_bearer='CLIENT',
            client=verified_client,
            loan=disbursed_loan,
            internal_reference='MOMO-2024-000001',
            status='INITIATED',
            initiated_by=loan_officer_user,
        )
        assert txn.transaction_type == 'COLLECTION'
        assert txn.direction == 'IN'
        assert txn.amount == Decimal('566.67')
        assert txn.status == 'INITIATED'

    def test_transaction_type_choices(self, tenant, mtn_provider, loan_officer_user, db):
        types = ['COLLECTION', 'DISBURSEMENT', 'DEPOSIT', 'WITHDRAWAL', 'REVERSAL']
        for i, ttype in enumerate(types):
            txn = MobileMoneyTransaction.objects.create(
                tenant=tenant,
                provider=mtn_provider,
                transaction_type=ttype,
                direction='IN',
                phone_number='+233244100001',
                amount=Decimal('100.00'),
                currency='GHS',
                internal_reference=f'MOMO-TYPE-{i:06d}',
                status='INITIATED',
                initiated_by=loan_officer_user,
            )
            assert txn.transaction_type == ttype

    def test_status_choices(self, tenant, mtn_provider, loan_officer_user, db):
        statuses = ['INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'REVERSED', 'TIMEOUT']
        for i, status in enumerate(statuses):
            txn = MobileMoneyTransaction.objects.create(
                tenant=tenant,
                provider=mtn_provider,
                transaction_type='COLLECTION',
                direction='IN',
                phone_number='+233244100001',
                amount=Decimal('100.00'),
                currency='GHS',
                internal_reference=f'MOMO-STAT-{i:06d}',
                status=status,
                initiated_by=loan_officer_user,
            )
            assert txn.status == status

    def test_reconciliation_tracking(self, tenant, mtn_provider, loan_officer_user, db):
        txn = MobileMoneyTransaction.objects.create(
            tenant=tenant,
            provider=mtn_provider,
            transaction_type='COLLECTION',
            direction='IN',
            phone_number='+233244100001',
            amount=Decimal('500.00'),
            currency='GHS',
            internal_reference='MOMO-RECON-000001',
            provider_reference='MTN-REF-ABC123',
            status='SUCCESS',
            initiated_by=loan_officer_user,
            reconciled=True,
            reconciled_at=timezone.now(),
        )
        assert txn.reconciled is True
        assert txn.provider_reference == 'MTN-REF-ABC123'

    def test_sync_fields(self, tenant, mtn_provider, loan_officer_user, db):
        txn = MobileMoneyTransaction.objects.create(
            tenant=tenant,
            provider=mtn_provider,
            transaction_type='COLLECTION',
            direction='IN',
            phone_number='+233244100001',
            amount=Decimal('100.00'),
            currency='GHS',
            internal_reference='MOMO-SYNC-000001',
            status='PENDING',
            initiated_by=loan_officer_user,
            device_id='field-agent-device-001',
            sync_status='PENDING_UPLOAD',
        )
        assert txn.device_id == 'field-agent-device-001'
        assert txn.sync_id is not None

    def test_direction_choices(self, tenant, mtn_provider, loan_officer_user, db):
        for i, direction in enumerate(['IN', 'OUT']):
            txn = MobileMoneyTransaction.objects.create(
                tenant=tenant,
                provider=mtn_provider,
                transaction_type='COLLECTION' if direction == 'IN' else 'DISBURSEMENT',
                direction=direction,
                phone_number='+233244100001',
                amount=Decimal('100.00'),
                currency='GHS',
                internal_reference=f'MOMO-DIR-{i:06d}',
                status='INITIATED',
                initiated_by=loan_officer_user,
            )
            assert txn.direction == direction
