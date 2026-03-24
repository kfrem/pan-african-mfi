"""
Shared pytest fixtures for the Pan-African MFI test suite.
Provides a complete, minimal data graph for all financial tests.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.tenants.models import CountryPack, LicenceTier, Tenant, Branch, RuleSetVersion, LicenceProfile
from apps.accounts.models import User, Role, Permission, RolePermission, UserRole
from apps.clients.models import Client, Group, GroupMember, KycDocument
from apps.loans.models import LoanProduct, Loan, RepaymentSchedule, Repayment
from apps.deposits.models import DepositProduct, DepositAccount, DepositTransaction
from apps.compliance.models import AmlAlert, Str, TransactionMonitoringRule, PrudentialReturn
from apps.ledger.models import GlAccount, GlTransaction, GlEntry, AccountingPeriod
from apps.investors.models import InvestorProfile, Dividend, InvestorShareLink
from apps.mobile_money.models import MobileMoneyProvider, MobileMoneyTransaction


# ─── COUNTRY & LICENCE ────────────────────────────────────────────────────────

@pytest.fixture
def country_gh(db):
    return CountryPack.objects.create(
        country_code='GH',
        country_name='Ghana',
        regulatory_authority='Bank of Ghana',
        default_currency='GHS',
        data_protection_law='Data Protection Act 2012',
        data_localisation_required=False,
        aml_supervisory_body='Financial Intelligence Centre',
        audit_retention_years=7,
        default_language='en',
        config={
            'classification_rules': {
                'CURRENT': {'days_past_due': [0, 30], 'provision_pct': 1},
                'WATCH': {'days_past_due': [31, 90], 'provision_pct': 5},
                'SUBSTANDARD': {'days_past_due': [91, 180], 'provision_pct': 25},
                'DOUBTFUL': {'days_past_due': [181, 360], 'provision_pct': 50},
                'LOSS': {'days_past_due': [361, 9999], 'provision_pct': 100},
            }
        },
        is_active=True,
    )


@pytest.fixture
def country_zm(db):
    return CountryPack.objects.create(
        country_code='ZM',
        country_name='Zambia',
        regulatory_authority='Bank of Zambia',
        default_currency='ZMW',
        data_protection_law='',
        data_localisation_required=False,
        aml_supervisory_body='Financial Intelligence Centre',
        audit_retention_years=7,
        default_language='en',
        config={},
        is_active=True,
    )


@pytest.fixture
def licence_tier(country_gh):
    return LicenceTier.objects.create(
        country=country_gh,
        tier_code='TIER_2',
        tier_name='Tier 2 MFI',
        can_accept_deposits=True,
        can_offer_savings=True,
        can_do_transfers=True,
        credit_only=False,
        min_capital_amount=Decimal('500000.00'),
        min_capital_currency='GHS',
        car_requirement_pct=Decimal('10.00'),
        single_obligor_limit_pct=Decimal('15.00'),
        insider_lending_limit_pct=Decimal('10.00'),
        reporting_frequency='MONTHLY',
    )


@pytest.fixture
def credit_only_tier(country_gh):
    return LicenceTier.objects.create(
        country=country_gh,
        tier_code='TIER_1_CREDIT',
        tier_name='Tier 1 Credit-Only',
        can_accept_deposits=False,
        can_offer_savings=False,
        can_do_transfers=False,
        credit_only=True,
        min_capital_amount=Decimal('100000.00'),
        min_capital_currency='GHS',
        car_requirement_pct=Decimal('15.00'),
        reporting_frequency='MONTHLY',
    )


@pytest.fixture
def tenant(country_gh, licence_tier):
    return Tenant.objects.create(
        name='Accra MFI Ltd',
        trading_name='AccraMFI',
        country=country_gh,
        licence_tier=licence_tier,
        status='ACTIVE',
        subscription_active=True,
        default_currency='GHS',
        default_language='en',
        timezone='Africa/Accra',
        logo_url='',
        primary_brand_colour='#004080',
        secondary_brand_colour='#FFD700',
        tagline='Banking the unbanked',
        data_localisation_required=False,
    )


@pytest.fixture
def branch(tenant):
    return Branch.objects.create(
        tenant=tenant,
        branch_code='HQ',
        branch_name='Head Office',
        branch_type='URBAN',
        address='1 Liberation Road, Accra',
        is_active=True,
    )


@pytest.fixture
def rural_branch(tenant):
    return Branch.objects.create(
        tenant=tenant,
        branch_code='RURAL-01',
        branch_name='Kumasi Rural Branch',
        branch_type='RURAL',
        address='Kumasi Market Area',
        is_active=True,
    )


@pytest.fixture
def rule_set_version(country_gh):
    return RuleSetVersion.objects.create(
        country=country_gh,
        rule_type='LOAN_CLASSIFICATION',
        version_code='BOG-2024',
        version_number=1,
        effective_from=date(2024, 1, 1),
        config={
            'CURRENT': {'days': 30, 'provision_pct': 1},
            'WATCH': {'days': 90, 'provision_pct': 5},
            'SUBSTANDARD': {'days': 180, 'provision_pct': 25},
            'DOUBTFUL': {'days': 360, 'provision_pct': 50},
            'LOSS': {'days': 9999, 'provision_pct': 100},
        },
    )


# ─── USERS & RBAC ─────────────────────────────────────────────────────────────

@pytest.fixture
def loan_officer_user(tenant, branch):
    return User.objects.create(
        tenant=tenant,
        auth_user_id=uuid.uuid4(),
        email='officer@accramfi.gh',
        full_name='Kwame Mensah',
        phone='+233244000001',
        branch=branch,
        is_active=True,
        is_locked=False,
        failed_login_count=0,
        mfa_enabled=False,
        language_preference='en',
        theme_preference='professional_light',
    )


@pytest.fixture
def manager_user(tenant, branch):
    return User.objects.create(
        tenant=tenant,
        auth_user_id=uuid.uuid4(),
        email='manager@accramfi.gh',
        full_name='Abena Osei',
        phone='+233244000002',
        branch=branch,
        is_active=True,
        is_locked=False,
        failed_login_count=0,
        mfa_enabled=True,
        language_preference='en',
        theme_preference='professional_dark',
    )


@pytest.fixture
def compliance_user(tenant, branch):
    return User.objects.create(
        tenant=tenant,
        auth_user_id=uuid.uuid4(),
        email='compliance@accramfi.gh',
        full_name='Ama Agyei',
        phone='+233244000003',
        branch=branch,
        is_active=True,
        is_locked=False,
        failed_login_count=0,
        mfa_enabled=True,
        language_preference='en',
        theme_preference='professional_light',
    )


@pytest.fixture
def locked_user(tenant, branch):
    return User.objects.create(
        tenant=tenant,
        auth_user_id=uuid.uuid4(),
        email='locked@accramfi.gh',
        full_name='Locked User',
        phone='+233244000099',
        branch=branch,
        is_active=True,
        is_locked=True,
        failed_login_count=5,
        mfa_enabled=False,
        language_preference='en',
        theme_preference='professional_light',
    )


@pytest.fixture
def role_loan_officer(tenant):
    return Role.objects.create(
        tenant=tenant,
        role_code='LOAN_OFFICER',
        role_name='Loan Officer',
        is_system_role=True,
        description='Creates and manages loan applications',
    )


@pytest.fixture
def role_credit_manager(tenant):
    return Role.objects.create(
        tenant=tenant,
        role_code='CREDIT_MANAGER',
        role_name='Credit Manager',
        is_system_role=True,
        description='Approves and oversees loans',
    )


@pytest.fixture
def role_compliance(tenant):
    return Role.objects.create(
        tenant=tenant,
        role_code='COMPLIANCE_OFFICER',
        role_name='Compliance Officer',
        is_system_role=True,
        description='Manages AML, KYC, and regulatory compliance',
    )


@pytest.fixture
def permission_loan_create(db):
    return Permission.objects.create(
        permission_code='LOAN:CREATE',
        resource='LOAN',
        action='CREATE',
        description='Create new loan applications',
    )


@pytest.fixture
def permission_loan_approve(db):
    return Permission.objects.create(
        permission_code='LOAN:APPROVE',
        resource='LOAN',
        action='APPROVE',
        description='Approve pending loan applications',
    )


@pytest.fixture
def permission_kyc_verify(db):
    return Permission.objects.create(
        permission_code='CLIENT:VERIFY_KYC',
        resource='CLIENT',
        action='VERIFY_KYC',
        description='Verify client KYC documents',
    )


@pytest.fixture
def permission_aml_review(db):
    return Permission.objects.create(
        permission_code='AML:REVIEW',
        resource='AML',
        action='REVIEW',
        description='Review AML alerts',
    )


# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@pytest.fixture
def individual_client(tenant, branch, loan_officer_user):
    return Client.objects.create(
        tenant=tenant,
        branch=branch,
        client_type='INDIVIDUAL',
        client_number='CLT-2024-00001',
        full_legal_name='Kofi Boateng',
        first_name='Kofi',
        middle_name='',
        last_name='Boateng',
        date_of_birth=date(1985, 6, 15),
        gender='MALE',
        national_id_type='GHANA_CARD',
        national_id_number='GHA-123456789-0',
        id_issue_date=date(2020, 1, 1),
        id_expiry_date=date(2030, 1, 1),
        phone_primary='+233244100001',
        phone_secondary='+233244100002',
        email='kofi.boateng@email.com',
        address_line_1='24 Tema Road',
        address_line_2='',
        city='Accra',
        region='Greater Accra',
        country='GH',
        occupation='Trader',
        employer_name='Self-employed',
        monthly_income=Decimal('2500.00'),
        income_currency='GHS',
        source_of_funds='Business income',
        risk_rating='LOW',
        is_pep=False,
        is_insider=False,
        insider_relationship='',
        kyc_status='COMPLETE',
        sanctions_checked=True,
        sanctions_hit=False,
        onboarding_blocked=False,
        block_reason='',
        assigned_officer=loan_officer_user,
    )


@pytest.fixture
def sme_client(tenant, branch, loan_officer_user):
    return Client.objects.create(
        tenant=tenant,
        branch=branch,
        client_type='SME',
        client_number='CLT-2024-00002',
        full_legal_name='Accra Traders Ltd',
        first_name='',
        last_name='',
        phone_primary='+233302100001',
        email='info@accratraders.gh',
        address_line_1='Ring Road Central',
        city='Accra',
        country='GH',
        occupation='Retail Trade',
        monthly_income=Decimal('15000.00'),
        income_currency='GHS',
        source_of_funds='Business revenue',
        risk_rating='MEDIUM',
        is_pep=False,
        is_insider=False,
        kyc_status='VERIFIED',
        sanctions_checked=True,
        sanctions_hit=False,
        onboarding_blocked=False,
        assigned_officer=loan_officer_user,
    )


@pytest.fixture
def pep_client(tenant, branch, loan_officer_user):
    """High-risk PEP client for compliance tests."""
    return Client.objects.create(
        tenant=tenant,
        branch=branch,
        client_type='INDIVIDUAL',
        client_number='CLT-2024-00003',
        full_legal_name='John Asante Mensah',
        first_name='John',
        last_name='Mensah',
        date_of_birth=date(1970, 3, 10),
        gender='MALE',
        national_id_type='GHANA_CARD',
        national_id_number='GHA-999999999-0',
        phone_primary='+233244999001',
        city='Accra',
        country='GH',
        occupation='Government Official',
        monthly_income=Decimal('8000.00'),
        income_currency='GHS',
        source_of_funds='Salary',
        risk_rating='HIGH',
        is_pep=True,
        is_insider=False,
        kyc_status='COMPLETE',
        sanctions_checked=True,
        sanctions_hit=False,
        onboarding_blocked=False,
        assigned_officer=loan_officer_user,
    )


@pytest.fixture
def insider_client(tenant, branch, loan_officer_user):
    """Insider (staff-related) client for compliance tests."""
    return Client.objects.create(
        tenant=tenant,
        branch=branch,
        client_type='INDIVIDUAL',
        client_number='CLT-2024-00004',
        full_legal_name='Akosua Mensah',
        first_name='Akosua',
        last_name='Mensah',
        date_of_birth=date(1988, 11, 20),
        gender='FEMALE',
        national_id_type='GHANA_CARD',
        national_id_number='GHA-111111111-0',
        phone_primary='+233244111001',
        city='Accra',
        country='GH',
        occupation='MFI Staff',
        monthly_income=Decimal('3500.00'),
        income_currency='GHS',
        source_of_funds='Salary',
        risk_rating='MEDIUM',
        is_pep=False,
        is_insider=True,
        insider_relationship='Spouse of Director',
        kyc_status='VERIFIED',
        sanctions_checked=True,
        sanctions_hit=False,
        onboarding_blocked=False,
        assigned_officer=loan_officer_user,
    )


@pytest.fixture
def blocked_client(tenant, branch, loan_officer_user):
    """Client blocked from onboarding due to sanctions hit."""
    return Client.objects.create(
        tenant=tenant,
        branch=branch,
        client_type='INDIVIDUAL',
        client_number='CLT-2024-00005',
        full_legal_name='Blocked Person',
        first_name='Blocked',
        last_name='Person',
        phone_primary='+233244555001',
        city='Accra',
        country='GH',
        occupation='Unknown',
        risk_rating='HIGH',
        is_pep=False,
        is_insider=False,
        kyc_status='INCOMPLETE',
        sanctions_checked=True,
        sanctions_hit=True,
        onboarding_blocked=True,
        block_reason='Sanctions match — OFAC list hit',
        assigned_officer=loan_officer_user,
    )


@pytest.fixture
def verified_client(individual_client, manager_user):
    """Client with VERIFIED KYC status — required for loan disbursement."""
    individual_client.kyc_status = 'VERIFIED'
    individual_client.kyc_verified_by = manager_user
    individual_client.kyc_verified_at = timezone.now()
    individual_client.save()
    return individual_client


@pytest.fixture
def group_entity(tenant, branch, individual_client):
    g = Group.objects.create(
        tenant=tenant,
        branch=branch,
        group_name='Accra Women Traders Group',
        group_number='GRP-2024-00001',
        leader=individual_client,
        meeting_frequency='WEEKLY',
        meeting_day='Monday',
        is_active=True,
    )
    GroupMember.objects.create(
        group=g,
        client=individual_client,
        joined_at=date(2024, 1, 10),
        is_active=True,
    )
    return g


@pytest.fixture
def kyc_document(tenant, individual_client, loan_officer_user):
    return KycDocument.objects.create(
        tenant=tenant,
        client=individual_client,
        document_type='ID_SCAN',
        file_path='kyc/CLT-2024-00001/ghana_card_scan.pdf',
        file_name='ghana_card_scan.pdf',
        file_size_bytes=256000,
        uploaded_by=loan_officer_user,
        verified=False,
        expiry_date=date(2030, 1, 1),
    )


# ─── LOAN PRODUCTS ────────────────────────────────────────────────────────────

@pytest.fixture
def flat_loan_product(tenant):
    return LoanProduct.objects.create(
        tenant=tenant,
        product_code='IND-FLAT-01',
        product_name='Individual Flat Loan',
        product_type='INDIVIDUAL',
        min_amount=Decimal('500.00'),
        max_amount=Decimal('50000.00'),
        min_term_months=1,
        max_term_months=24,
        interest_method='FLAT',
        default_interest_rate_pct=Decimal('3.0000'),
        origination_fee_pct=Decimal('2.00'),
        insurance_fee_pct=Decimal('0.50'),
        requires_collateral=False,
        requires_guarantor=False,
        allowed_frequencies=['MONTHLY', 'WEEKLY'],
        is_active=True,
    )


@pytest.fixture
def reducing_loan_product(tenant):
    return LoanProduct.objects.create(
        tenant=tenant,
        product_code='SME-RB-01',
        product_name='SME Reducing Balance Loan',
        product_type='SME',
        min_amount=Decimal('5000.00'),
        max_amount=Decimal('500000.00'),
        min_term_months=3,
        max_term_months=60,
        interest_method='REDUCING_BALANCE',
        default_interest_rate_pct=Decimal('2.5000'),
        origination_fee_pct=Decimal('1.50'),
        insurance_fee_pct=Decimal('0.25'),
        requires_collateral=True,
        requires_guarantor=True,
        allowed_frequencies=['MONTHLY'],
        is_active=True,
    )


@pytest.fixture
def group_loan_product(tenant):
    return LoanProduct.objects.create(
        tenant=tenant,
        product_code='GRP-JOINT-01',
        product_name='Group Joint Liability Loan',
        product_type='GROUP',
        min_amount=Decimal('200.00'),
        max_amount=Decimal('10000.00'),
        min_term_months=3,
        max_term_months=12,
        interest_method='FLAT',
        default_interest_rate_pct=Decimal('2.0000'),
        origination_fee_pct=Decimal('1.00'),
        insurance_fee_pct=Decimal('0.50'),
        requires_collateral=False,
        requires_guarantor=False,
        group_liability_type='JOINT',
        allowed_frequencies=['WEEKLY', 'MONTHLY'],
        is_active=True,
    )


# ─── LOANS ────────────────────────────────────────────────────────────────────

@pytest.fixture
def pending_loan(tenant, branch, verified_client, flat_loan_product, loan_officer_user):
    principal = Decimal('5000.00')
    rate = Decimal('3.0000')
    term = 12
    total_interest = principal * (rate / 100) * (Decimal(str(term)) / 12)
    origination_fee = principal * (Decimal('2.00') / 100)
    total_repayable = principal + total_interest + origination_fee
    return Loan.objects.create(
        tenant=tenant,
        loan_number='LN-202401-00001',
        client=verified_client,
        product=flat_loan_product,
        branch=branch,
        loan_officer=loan_officer_user,
        principal_amount=principal,
        currency='GHS',
        interest_rate_pct=rate,
        interest_method='FLAT',
        term_months=term,
        repayment_frequency='MONTHLY',
        origination_fee=origination_fee,
        insurance_fee=Decimal('25.00'),
        total_interest=total_interest,
        total_repayable=total_repayable,
        outstanding_principal=principal,
        outstanding_interest=total_interest,
        arrears_amount=Decimal('0.00'),
        days_past_due=0,
        status='PENDING_APPROVAL',
        classification='CURRENT',
        provision_rate_pct=Decimal('1.00'),
        provision_amount=Decimal('0.00'),
        application_date=date.today(),
        is_insider_loan=False,
        override_flag=False,
        collateral_description='',
    )


@pytest.fixture
def approved_loan(pending_loan, manager_user):
    pending_loan.status = 'APPROVED'
    pending_loan.approval_date = date.today()
    pending_loan.approved_by = manager_user
    pending_loan.save()
    return pending_loan


@pytest.fixture
def disbursed_loan(approved_loan, manager_user):
    today = date.today()
    approved_loan.status = 'DISBURSED'
    approved_loan.disbursement_date = today
    approved_loan.maturity_date = today + timedelta(days=365)
    approved_loan.first_repayment_date = today + timedelta(days=30)
    approved_loan.disbursed_by = manager_user
    approved_loan.save()
    return approved_loan


@pytest.fixture
def overdue_loan(disbursed_loan):
    """Loan that is 45 days past due — WATCH classification."""
    disbursed_loan.days_past_due = 45
    disbursed_loan.arrears_amount = Decimal('416.67')
    disbursed_loan.classification = 'WATCH'
    disbursed_loan.provision_rate_pct = Decimal('5.00')
    disbursed_loan.provision_amount = disbursed_loan.outstanding_principal * Decimal('0.05')
    disbursed_loan.save()
    return disbursed_loan


@pytest.fixture
def loss_loan(disbursed_loan):
    """Loan >360 DPD — LOSS classification, 100% provision."""
    disbursed_loan.days_past_due = 400
    disbursed_loan.arrears_amount = disbursed_loan.outstanding_principal
    disbursed_loan.classification = 'LOSS'
    disbursed_loan.provision_rate_pct = Decimal('100.00')
    disbursed_loan.provision_amount = disbursed_loan.outstanding_principal
    disbursed_loan.save()
    return disbursed_loan


@pytest.fixture
def insider_loan(tenant, branch, insider_client, flat_loan_product, loan_officer_user):
    """Loan flagged as insider — requires enhanced controls."""
    principal = Decimal('20000.00')
    rate = Decimal('3.0000')
    term = 12
    total_interest = principal * (rate / 100)
    origination_fee = principal * (Decimal('2.00') / 100)
    total_repayable = principal + total_interest + origination_fee
    return Loan.objects.create(
        tenant=tenant,
        loan_number='LN-202401-00099',
        client=insider_client,
        product=flat_loan_product,
        branch=branch,
        loan_officer=loan_officer_user,
        principal_amount=principal,
        currency='GHS',
        interest_rate_pct=rate,
        interest_method='FLAT',
        term_months=term,
        repayment_frequency='MONTHLY',
        origination_fee=origination_fee,
        insurance_fee=Decimal('0.00'),
        total_interest=total_interest,
        total_repayable=total_repayable,
        outstanding_principal=principal,
        outstanding_interest=total_interest,
        arrears_amount=Decimal('0.00'),
        days_past_due=0,
        status='PENDING_APPROVAL',
        classification='CURRENT',
        provision_rate_pct=Decimal('1.00'),
        provision_amount=Decimal('0.00'),
        application_date=date.today(),
        is_insider_loan=True,
        override_flag=False,
        collateral_description='',
    )


@pytest.fixture
def repayment_schedule(disbursed_loan, tenant):
    """Single monthly instalment for the disbursed loan."""
    return RepaymentSchedule.objects.create(
        tenant=tenant,
        loan=disbursed_loan,
        instalment_number=1,
        due_date=date.today() + timedelta(days=30),
        principal_due=Decimal('416.67'),
        interest_due=Decimal('150.00'),
        fees_due=Decimal('0.00'),
        total_due=Decimal('566.67'),
        principal_paid=Decimal('0.00'),
        interest_paid=Decimal('0.00'),
        total_paid=Decimal('0.00'),
        balance_after=Decimal('4583.33'),
        status='PENDING',
        days_late=0,
    )


# ─── DEPOSITS ─────────────────────────────────────────────────────────────────

@pytest.fixture
def savings_product(tenant):
    return DepositProduct.objects.create(
        tenant=tenant,
        product_code='SAV-001',
        product_name='Standard Savings',
        product_type='SAVINGS',
        interest_rate_pct=Decimal('5.0000'),
        min_balance=Decimal('20.00'),
        notice_period_days=0,
        is_active=True,
    )


@pytest.fixture
def fixed_deposit_product(tenant):
    return DepositProduct.objects.create(
        tenant=tenant,
        product_code='FD-001',
        product_name='12-Month Fixed Deposit',
        product_type='FIXED_DEPOSIT',
        interest_rate_pct=Decimal('12.0000'),
        min_balance=Decimal('1000.00'),
        notice_period_days=30,
        is_active=True,
    )


@pytest.fixture
def deposit_account(tenant, verified_client, savings_product):
    return DepositAccount.objects.create(
        tenant=tenant,
        client=verified_client,
        product=savings_product,
        account_number='SAV-2024-00001',
        currency='GHS',
        balance=Decimal('500.00'),
        status='ACTIVE',
        opened_at=date.today() - timedelta(days=90),
    )


@pytest.fixture
def fixed_deposit_account(tenant, verified_client, fixed_deposit_product):
    return DepositAccount.objects.create(
        tenant=tenant,
        client=verified_client,
        product=fixed_deposit_product,
        account_number='FD-2024-00001',
        currency='GHS',
        balance=Decimal('5000.00'),
        status='ACTIVE',
        opened_at=date.today() - timedelta(days=30),
        maturity_date=date.today() + timedelta(days=335),
    )


# ─── GL / LEDGER ──────────────────────────────────────────────────────────────

@pytest.fixture
def gl_cash_account(tenant):
    return GlAccount.objects.create(
        tenant=tenant,
        account_code='1001',
        account_name='Cash in Vault',
        account_type='ASSET',
        normal_balance='D',
        is_header=False,
        is_system_account=True,
        currency='GHS',
        is_active=True,
    )


@pytest.fixture
def gl_loan_account(tenant):
    return GlAccount.objects.create(
        tenant=tenant,
        account_code='2001',
        account_name='Loans Receivable',
        account_type='ASSET',
        normal_balance='D',
        is_header=False,
        is_system_account=True,
        currency='GHS',
        is_active=True,
    )


@pytest.fixture
def gl_interest_income(tenant):
    return GlAccount.objects.create(
        tenant=tenant,
        account_code='4001',
        account_name='Interest Income',
        account_type='INCOME',
        normal_balance='C',
        is_header=False,
        is_system_account=True,
        currency='GHS',
        is_active=True,
    )


@pytest.fixture
def gl_deposit_liability(tenant):
    return GlAccount.objects.create(
        tenant=tenant,
        account_code='3001',
        account_name='Customer Deposits',
        account_type='LIABILITY',
        normal_balance='C',
        is_header=False,
        is_system_account=True,
        currency='GHS',
        is_active=True,
    )


@pytest.fixture
def accounting_period(tenant):
    return AccountingPeriod.objects.create(
        tenant=tenant,
        period_name='January 2024',
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        status='OPEN',
    )


# ─── COMPLIANCE ───────────────────────────────────────────────────────────────

@pytest.fixture
def aml_alert(tenant, individual_client, compliance_user):
    return AmlAlert.objects.create(
        tenant=tenant,
        client=individual_client,
        alert_type='THRESHOLD',
        trigger_description='Single transaction exceeds GHS 10,000 threshold',
        trigger_amount=Decimal('12000.00'),
        trigger_currency='GHS',
        status='OPEN',
        assigned_to=compliance_user,
        risk_score=75,
    )


@pytest.fixture
def monitoring_rule(country_gh):
    return TransactionMonitoringRule.objects.create(
        country=country_gh,
        rule_code='GH-THRESH-001',
        rule_name='Single Transaction Threshold',
        rule_type='THRESHOLD',
        config={'threshold_amount': 10000, 'currency': 'GHS'},
        severity='HIGH',
        is_active=True,
    )


@pytest.fixture
def prudential_return(tenant, compliance_user):
    return PrudentialReturn.objects.create(
        tenant=tenant,
        return_template_code='BOG-MFI-MONTHLY',
        return_name='Monthly MFI Return',
        reporting_period='2024-01',
        due_date=date(2024, 2, 15),
        status='PENDING',
        generated_by=compliance_user,
        generated_at=timezone.now(),
    )


# ─── MOBILE MONEY ─────────────────────────────────────────────────────────────

@pytest.fixture
def mtn_provider(country_gh, gl_cash_account):
    return MobileMoneyProvider.objects.create(
        country=country_gh,
        provider_code='MTN_GH',
        provider_name='MTN Mobile Money',
        api_type='AFRICAS_TALKING',
        api_config={},
        currency='GHS',
        phone_prefix='024',
        phone_regex=r'^024\d{7}$',
        min_transaction=Decimal('1.00'),
        max_transaction=Decimal('10000.00'),
        fee_structure={'percentage': 0.01, 'flat': 0},
        settlement_gl_account=gl_cash_account,
        is_active=True,
    )


# ─── INVESTORS ────────────────────────────────────────────────────────────────

@pytest.fixture
def investor_profile(tenant, manager_user):
    return InvestorProfile.objects.create(
        tenant=tenant,
        user=manager_user,
        investor_name='AfricaGrowth Fund',
        investor_type='FUND',
        investment_currency='USD',
        invested_amount=Decimal('500000.00'),
        invested_amount_local=Decimal('6250000.00'),
        investment_date=date(2024, 1, 1),
        exchange_rate_at_investment=Decimal('12.50000000'),
        current_value_local=Decimal('6500000.00'),
        status='ACTIVE',
        covenant_thresholds={
            'par30_max_pct': 5.0,
            'car_min_pct': 15.0,
        },
    )
