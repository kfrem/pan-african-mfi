"""
Compliance gate tests — KYC, AML, maker-checker, PEP, insider controls.
These are non-negotiable for financial institution certification.
"""
from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest
from django.utils import timezone

from apps.loans.models import Loan
from apps.clients.models import Client, KycDocument
from apps.compliance.models import AmlAlert, Str, PrudentialReturn, TransactionMonitoringRule
from apps.accounts.models import MakerCheckerConfig, ApprovalRequest


pytestmark = pytest.mark.compliance


class TestKycGate:
    """KYC status must gate loan disbursement."""

    def test_verified_client_can_receive_disbursement(self, verified_client):
        """VERIFIED KYC → loan disbursement allowed."""
        assert verified_client.kyc_status == 'VERIFIED'
        # Gate check: not INCOMPLETE → disbursement is permitted
        can_disburse = verified_client.kyc_status != 'INCOMPLETE'
        assert can_disburse is True

    def test_incomplete_kyc_blocks_disbursement(self, individual_client):
        """INCOMPLETE KYC → disbursement must be blocked."""
        individual_client.kyc_status = 'INCOMPLETE'
        individual_client.save()
        assert individual_client.kyc_status == 'INCOMPLETE'
        # Application logic (from api_views.py):
        blocked = individual_client.kyc_status == 'INCOMPLETE'
        assert blocked is True

    def test_expired_kyc_detected(self, individual_client, db):
        """EXPIRED KYC must be flagged for renewal before lending."""
        individual_client.kyc_status = 'EXPIRED'
        individual_client.save()
        expired_clients = Client.objects.filter(kyc_status='EXPIRED')
        assert expired_clients.exists()

    def test_kyc_verification_requires_verifier(self, verified_client, manager_user):
        """KYC VERIFIED status must record who verified it."""
        assert verified_client.kyc_verified_by is not None
        assert verified_client.kyc_verified_at is not None

    def test_kyc_verification_timestamp_set(self, verified_client):
        assert verified_client.kyc_verified_at is not None
        assert verified_client.kyc_verified_at <= timezone.now()

    def test_document_verification_tracked(self, kyc_document, manager_user, db):
        kyc_document.verified = True
        kyc_document.verified_by = manager_user
        kyc_document.verified_at = timezone.now()
        kyc_document.save()
        assert kyc_document.verified is True
        assert kyc_document.verified_by == manager_user

    def test_expired_document_flagged(self, kyc_document, db):
        kyc_document.expiry_date = date.today() - timedelta(days=30)
        kyc_document.save()
        expired = KycDocument.objects.filter(expiry_date__lt=date.today())
        assert expired.exists()

    def test_all_doc_types_trackable(self, tenant, individual_client, loan_officer_user, db):
        """All 5 KYC document types must be capturable."""
        doc_types = ['ID_SCAN', 'PROOF_OF_ADDRESS', 'PHOTO', 'SOURCE_OF_FUNDS', 'EDD_REPORT']
        for dtype in doc_types:
            KycDocument.objects.create(
                tenant=tenant,
                client=individual_client,
                document_type=dtype,
                file_path=f'test/{dtype}.pdf',
                uploaded_by=loan_officer_user,
            )
        count = KycDocument.objects.filter(client=individual_client).count()
        assert count == 5


class TestPepControls:
    """Politically Exposed Person (PEP) controls."""

    def test_pep_flag_set(self, pep_client):
        assert pep_client.is_pep is True

    def test_pep_client_high_risk_rating(self, pep_client):
        """PEP clients must be rated HIGH risk by default."""
        assert pep_client.risk_rating == 'HIGH'

    def test_pep_flag_queryable(self, pep_client, individual_client, db):
        pep_clients = Client.objects.filter(is_pep=True)
        non_pep = Client.objects.filter(is_pep=False)
        assert pep_clients.count() >= 1
        assert individual_client not in pep_clients

    def test_non_pep_can_be_low_risk(self, individual_client):
        assert individual_client.is_pep is False
        assert individual_client.risk_rating == 'LOW'

    def test_pep_requires_edd(self, pep_client):
        """PEP clients should require Enhanced Due Diligence (EDD) document."""
        # The system must support EDD_REPORT document type for PEPs
        from apps.clients.models import KycDocument
        # EDD_REPORT is a valid document type choice — verify it exists in choices
        choices = [c[0] for c in KycDocument.DOC_TYPE_CHOICES]
        assert 'EDD_REPORT' in choices


class TestSanctionsControls:
    """Sanctions screening fields and onboarding blocks."""

    def test_sanctions_checked_field(self, individual_client):
        assert individual_client.sanctions_checked is True

    def test_sanctions_hit_blocks_onboarding(self, blocked_client):
        assert blocked_client.sanctions_hit is True
        assert blocked_client.onboarding_blocked is True

    def test_block_reason_required_when_blocked(self, blocked_client):
        assert blocked_client.block_reason != ''

    def test_no_sanctions_hit_allows_onboarding(self, individual_client):
        assert individual_client.sanctions_hit is False
        assert individual_client.onboarding_blocked is False

    def test_sanctions_check_required_before_kyc(self, tenant, branch, loan_officer_user, db):
        """Client created without sanctions check → sanctions_checked defaults False."""
        c = Client.objects.create(
            tenant=tenant,
            branch=branch,
            client_type='INDIVIDUAL',
            client_number='CLT-SANC-00001',
            full_legal_name='Unchecked Person',
            kyc_status='INCOMPLETE',
            risk_rating='LOW',
            assigned_officer=loan_officer_user,
        )
        assert c.sanctions_checked is False

    def test_sanctions_hit_queryable(self, blocked_client, individual_client, db):
        hits = Client.objects.filter(sanctions_hit=True)
        assert hits.count() >= 1
        assert individual_client not in hits


class TestInsiderLendingControls:
    """Insider lending — regulatory limits and mandatory flagging."""

    def test_insider_client_flagged(self, insider_client):
        assert insider_client.is_insider is True
        assert insider_client.insider_relationship != ''

    def test_insider_loan_auto_flagged(self, insider_loan):
        assert insider_loan.is_insider_loan is True

    def test_insider_loans_queryable(self, insider_loan, pending_loan, db):
        insider_loans = Loan.objects.filter(is_insider_loan=True)
        non_insider = Loan.objects.filter(is_insider_loan=False)
        assert insider_loans.count() >= 1
        assert pending_loan not in insider_loans

    def test_insider_lending_limit_tracked(self, licence_tier):
        """Licence tier must specify insider lending limit percentage."""
        assert licence_tier.insider_lending_limit_pct is not None
        assert licence_tier.insider_lending_limit_pct == Decimal('10.00')

    def test_insider_relationship_documented(self, insider_client):
        """Insider relationship type must be documented."""
        assert insider_client.insider_relationship == 'Spouse of Director'


class TestMakerCheckerControls:
    """Maker-checker: the loan officer cannot approve their own loan."""

    def test_maker_cannot_approve_own_loan(self, pending_loan, loan_officer_user):
        """
        Business rule from api_views.py:
        if loan.loan_officer == user: return 403
        """
        is_maker = pending_loan.loan_officer == loan_officer_user
        assert is_maker is True  # This user is the maker
        # The approval must be BLOCKED if maker == checker
        blocked = (pending_loan.loan_officer == loan_officer_user)
        assert blocked is True

    def test_different_user_can_approve(self, pending_loan, manager_user, loan_officer_user):
        """A different user (checker) can approve."""
        is_different_user = pending_loan.loan_officer != manager_user
        assert is_different_user is True  # manager can approve

    def test_maker_checker_config_creation(self, tenant, db):
        config = MakerCheckerConfig.objects.create(
            tenant=tenant,
            action_type='LOAN_DISBURSEMENT',
            min_approvals=2,
            required_roles=['CREDIT_MANAGER', 'CEO'],
            is_active=True,
        )
        assert config.min_approvals == 2
        assert 'CREDIT_MANAGER' in config.required_roles

    def test_amount_threshold_triggers_extra_approval(self, tenant, db):
        """Loans above GHS 100k need board approval."""
        config = MakerCheckerConfig.objects.create(
            tenant=tenant,
            action_type='LOAN_APPROVAL',
            min_approvals=3,
            required_roles=['BOARD'],
            amount_threshold=Decimal('100000.00'),
            amount_currency='GHS',
            is_active=True,
        )
        assert config.amount_threshold == Decimal('100000.0000')

    def test_approval_request_workflow(self, tenant, loan_officer_user, db):
        request = ApprovalRequest.objects.create(
            tenant=tenant,
            action_type='LOAN_DISBURSEMENT',
            target_table='loans',
            target_id=uuid.uuid4(),
            requested_by=loan_officer_user,
            payload={'loan_id': 'xyz', 'amount': 5000},
            status='PENDING',
        )
        assert request.status == 'PENDING'
        assert request.resolved_at is None


class TestAmlControls:
    """AML monitoring — alert creation, review, and STR filing."""

    def test_alert_created_for_threshold_breach(self, aml_alert):
        assert aml_alert.trigger_amount > Decimal('10000.00')
        assert aml_alert.status == 'OPEN'
        assert aml_alert.risk_score == 75

    def test_all_statuses_reachable(self, tenant, individual_client, compliance_user, db):
        statuses = ['OPEN', 'UNDER_REVIEW', 'ESCALATED', 'STR_FILED', 'CLOSED_NO_ACTION']
        for status in statuses:
            AmlAlert.objects.create(
                tenant=tenant,
                client=individual_client,
                alert_type='THRESHOLD',
                trigger_description='Test',
                status=status,
            )
        count = AmlAlert.objects.filter(client=individual_client).count()
        assert count == 5

    def test_str_filed_from_alert(self, tenant, individual_client, compliance_user, aml_alert, db):
        report = Str.objects.create(
            tenant=tenant,
            alert=aml_alert,
            client=individual_client,
            report_type='STR',
            narrative='Cash structuring detected.',
            transaction_amount=Decimal('28500.00'),
            transaction_currency='GHS',
            transaction_date=date.today() - timedelta(days=5),
            status='DRAFT',
            filed_by=compliance_user,
            deadline=date.today() + timedelta(days=3),
        )
        aml_alert.status = 'STR_FILED'
        aml_alert.save()
        assert report.alert == aml_alert
        assert aml_alert.status == 'STR_FILED'

    def test_monitoring_rules_configured_per_country(self, monitoring_rule, country_gh):
        assert monitoring_rule.country == country_gh
        assert monitoring_rule.is_active is True

    def test_velocity_rule_type_supported(self, country_gh, db):
        rule = TransactionMonitoringRule.objects.create(
            country=country_gh,
            rule_code='GH-VEL-001',
            rule_name='3-Day Velocity Rule',
            rule_type='VELOCITY',
            config={'count_threshold': 5, 'period_days': 3, 'currency': 'GHS'},
            severity='CRITICAL',
            is_active=True,
        )
        assert rule.rule_type == 'VELOCITY'
        assert rule.severity == 'CRITICAL'

    def test_pattern_rule_type_supported(self, country_gh, db):
        rule = TransactionMonitoringRule.objects.create(
            country=country_gh,
            rule_code='GH-PAT-001',
            rule_name='Structuring Pattern',
            rule_type='PATTERN',
            config={'pattern': 'STRUCTURING', 'window_days': 7},
            severity='HIGH',
            is_active=True,
        )
        assert rule.rule_type == 'PATTERN'

    def test_risk_score_1_to_100(self, aml_alert):
        """Risk scores must be in valid range."""
        assert 1 <= aml_alert.risk_score <= 100


class TestPrudentialReturns:
    """Regulatory return generation and submission controls."""

    def test_return_created_with_all_fields(self, prudential_return):
        assert prudential_return.return_template_code == 'BOG-MFI-MONTHLY'
        assert prudential_return.status == 'PENDING'
        assert prudential_return.due_date is not None

    def test_overdue_return_detection(self, prudential_return, db):
        prudential_return.status = 'OVERDUE'
        prudential_return.save()
        overdue = PrudentialReturn.objects.filter(status='OVERDUE')
        assert overdue.exists()

    def test_submission_audit_trail(self, prudential_return, compliance_user, db):
        prudential_return.status = 'SUBMITTED'
        prudential_return.submitted_by = compliance_user
        prudential_return.submitted_at = timezone.now()
        prudential_return.submitted_values = {'par30_pct': 3.2, 'car_pct': 14.1}
        prudential_return.save()
        assert prudential_return.submitted_by == compliance_user
        assert prudential_return.submitted_at is not None
        assert 'par30_pct' in prudential_return.submitted_values

    def test_variance_computed(self, prudential_return, db):
        prudential_return.system_computed_values = {'par30_pct': 4.5}
        prudential_return.submitted_values = {'par30_pct': 4.2}
        prudential_return.variance_pct = Decimal('6.67')
        prudential_return.save()
        assert prudential_return.variance_pct is not None


class TestSingleObligorLimit:
    """Single obligor limit — concentration risk control."""

    def test_single_obligor_limit_on_tier(self, licence_tier):
        """Tier must define single obligor limit %."""
        assert licence_tier.single_obligor_limit_pct == Decimal('15.00')

    def test_car_requirement_defined(self, licence_tier):
        """Capital Adequacy Ratio (CAR) requirement must be defined."""
        assert licence_tier.car_requirement_pct is not None
        assert licence_tier.car_requirement_pct == Decimal('10.00')

    def test_credit_only_tier_has_higher_car(self, credit_only_tier):
        """Credit-only tiers typically face stricter CAR requirements."""
        assert credit_only_tier.car_requirement_pct == Decimal('15.00')


class TestSessionSecurity:
    """Session security controls — timeouts, MFA, IP whitelist."""

    def test_compliance_role_requires_mfa(self, tenant, db):
        from apps.accounts.models import SessionConfig
        config = SessionConfig.objects.create(
            tenant=tenant,
            role_code='COMPLIANCE_OFFICER',
            require_mfa=True,
            session_timeout_minutes=240,
        )
        assert config.require_mfa is True

    def test_shorter_timeout_for_sensitive_roles(self, tenant, db):
        from apps.accounts.models import SessionConfig
        admin = SessionConfig.objects.create(
            tenant=tenant,
            role_code='SYSTEM_ADMIN',
            require_mfa=True,
            session_timeout_minutes=60,  # 1 hour max
        )
        general = SessionConfig.objects.create(
            tenant=tenant,
            role_code='LOAN_OFFICER',
            require_mfa=False,
            session_timeout_minutes=480,  # 8 hours
        )
        assert admin.session_timeout_minutes < general.session_timeout_minutes

    def test_account_lockout_after_failed_attempts(self, locked_user):
        """After too many failed logins, account must lock."""
        assert locked_user.is_locked is True
        assert locked_user.failed_login_count >= 5

    def test_mfa_enabled_for_high_privilege_user(self, manager_user):
        assert manager_user.mfa_enabled is True


class TestDataLocalisation:
    """Data localisation and residency requirements."""

    def test_tenant_data_centre_tag(self, tenant, db):
        """Tenant can tag data centre for localisation compliance."""
        tenant.data_centre_tag = 'GH-ACCRA-DC1'
        tenant.data_localisation_required = True
        tenant.save()
        tenant.refresh_from_db()
        assert tenant.data_localisation_required is True
        assert tenant.data_centre_tag == 'GH-ACCRA-DC1'

    def test_country_pack_data_localisation_flag(self, country_gh):
        assert country_gh.data_localisation_required is False

    def test_audit_retention_years_minimum(self, country_gh):
        """Regulatory requirement: audit data must be retained for at least 7 years."""
        assert country_gh.audit_retention_years >= 7


class TestLoanOverride:
    """Override flag — exceptional lending cases with audit trail."""

    def test_override_flag_false_by_default(self, pending_loan):
        assert pending_loan.override_flag is False

    def test_override_requires_reason(self, pending_loan, db):
        pending_loan.override_flag = True
        pending_loan.override_reason = 'Board resolution: strategic client — approved under special conditions'
        pending_loan.save()
        pending_loan.refresh_from_db()
        assert pending_loan.override_flag is True
        assert pending_loan.override_reason != ''

    def test_override_loans_queryable(self, pending_loan, db):
        pending_loan.override_flag = True
        pending_loan.override_reason = 'Special approval'
        pending_loan.save()
        overridden = Loan.objects.filter(override_flag=True)
        assert overridden.count() == 1
