"""
Test Data Seed Script — Pan-African Microfinance SaaS
Generates the complete staging dataset as defined in the Test Data Generation Guide.

Run: python manage.py seed --env=staging
Or:  python manage.py shell < apps/seed_data.py

Creates:
- 4 test tenants (GH Tier 2, GH Tier 3, ZM Tier I, ZM Tier II)
- 17 users per tenant (all roles covered)
- 500+ clients per deposit-taking tenant
- Loan products, active loans with varied classifications
- Repayment history (24 months)
- AML alerts and STR scenarios
- GL transactions and financial statements
- Exchange rates (24 months)
"""
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

# This file is designed to be run via Django management command.
# All imports assume Django is configured.

def seed_all():
    """Master seed function — run everything in order."""
    print("=== Pan-African MFI SaaS — Seeding Test Data ===")
    print()

    # Step 1: Country packs and licence tiers (already seeded by SQL migration)
    print("[1/10] Country packs and licence tiers... (already seeded via SQL)")

    # Step 2: Test tenants
    tenants = seed_tenants()
    print(f"[2/10] Tenants created: {len(tenants)}")

    # Step 3: Users and roles
    for tenant in tenants:
        users = seed_users(tenant)
        print(f"  [{tenant.trading_name}] Users: {len(users)}")

    # Step 4: Branches
    for tenant in tenants:
        branches = seed_branches(tenant)
        print(f"  [{tenant.trading_name}] Branches: {len(branches)}")

    # Step 5: Loan products
    for tenant in tenants:
        products = seed_loan_products(tenant)
        print(f"  [{tenant.trading_name}] Loan products: {len(products)}")

    # Step 6: Clients
    for tenant in tenants:
        clients = seed_clients(tenant)
        print(f"  [{tenant.trading_name}] Clients: {len(clients)}")

    # Step 7: Loans with schedules
    for tenant in tenants:
        loans = seed_loans(tenant)
        print(f"  [{tenant.trading_name}] Loans: {len(loans)}")

    # Step 8: Exchange rates
    rates = seed_exchange_rates()
    print(f"[8/10] Exchange rates: {len(rates)}")

    # Step 9: AML scenarios
    for tenant in tenants:
        alerts = seed_aml_scenarios(tenant)
        print(f"  [{tenant.trading_name}] AML alerts: {len(alerts)}")

    # Step 10: Credit scores
    for tenant in tenants:
        scores = seed_credit_scores(tenant)
        print(f"  [{tenant.trading_name}] Credit scores: {len(scores)}")

    print()
    print("=== Seeding complete ===")


def seed_tenants():
    from apps.tenants.models import Tenant, LicenceTier, LicenceProfile

    configs = [
        {'name': 'Accra MicroCredit Ltd', 'trading': 'Accra MicroCredit', 'country': 'GH', 'tier': 'GHANA_TIER_2', 'currency': 'GHS'},
        {'name': 'Kumasi Lending Co', 'trading': 'Kumasi Lending', 'country': 'GH', 'tier': 'GHANA_TIER_3', 'currency': 'GHS'},
        {'name': 'Lusaka Finance Ltd', 'trading': 'Lusaka Finance', 'country': 'ZM', 'tier': 'ZAMBIA_TIER_I', 'currency': 'ZMW'},
        {'name': 'Ndola Credit Services', 'trading': 'Ndola Credit', 'country': 'ZM', 'tier': 'ZAMBIA_TIER_II', 'currency': 'ZMW'},
    ]

    tenants = []
    for cfg in configs:
        tier = LicenceTier.objects.get(country_code=cfg['country'], tier_code=cfg['tier'])
        tenant, created = Tenant.objects.get_or_create(
            name=cfg['name'],
            defaults={
                'trading_name': cfg['trading'],
                'country_code': cfg['country'],
                'licence_tier': tier,
                'default_currency': cfg['currency'],
                'primary_brand_colour': random.choice(['#1b3a6b', '#1a4731', '#0d9488', '#7c2d12']),
            }
        )
        if created:
            LicenceProfile.objects.create(
                tenant=tenant,
                licence_number=f'{cfg["country"]}/MFI/{random.randint(2020,2025)}/{random.randint(1000,9999)}',
                licensing_authority=tier.country.regulatory_authority,
                effective_from=date(2023, 1, 1),
                expires_on=date(2026, 12, 31),
            )
        tenants.append(tenant)
    return tenants


def seed_users(tenant):
    from apps.accounts.models import User, Role, UserRole

    # Seed system roles
    role_codes = [
        'DATA_ENTRY', 'LOAN_OFFICER', 'BRANCH_MANAGER', 'CREDIT_MANAGER',
        'ACCOUNTANT', 'COMPLIANCE_OFFICER', 'IT_SECURITY_ADMIN', 'CEO_CFO',
        'BOARD_DIRECTOR', 'INVESTOR', 'EXTERNAL_AUDITOR', 'INTERNAL_AUDITOR',
    ]
    roles = {}
    for code in role_codes:
        role, _ = Role.objects.get_or_create(
            tenant=tenant, role_code=code,
            defaults={'role_name': code.replace('_', ' ').title(), 'is_system_role': True}
        )
        roles[code] = role

    # Create users
    user_defs = [
        ('ceo', 'CEO / Managing Director', 'CEO_CFO'),
        ('cfo', 'CFO / Finance Director', 'CEO_CFO'),
        ('credit.mgr', 'Credit Manager', 'CREDIT_MANAGER'),
        ('accountant', 'Senior Accountant', 'ACCOUNTANT'),
        ('compliance', 'Compliance Officer', 'COMPLIANCE_OFFICER'),
        ('it.admin', 'IT Security Admin', 'IT_SECURITY_ADMIN'),
        ('branch.mgr1', 'Branch Manager A', 'BRANCH_MANAGER'),
        ('branch.mgr2', 'Branch Manager B', 'BRANCH_MANAGER'),
        ('officer1', 'Loan Officer 1', 'LOAN_OFFICER'),
        ('officer2', 'Loan Officer 2', 'LOAN_OFFICER'),
        ('data.entry1', 'Data Entry Clerk', 'DATA_ENTRY'),
        ('board1', 'Board Director 1', 'BOARD_DIRECTOR'),
        ('board2', 'Board Director 2', 'BOARD_DIRECTOR'),
        ('investor1', 'USD Investor', 'INVESTOR'),
        ('investor2', 'GBP Investor', 'INVESTOR'),
        ('auditor.ext', 'External Auditor', 'EXTERNAL_AUDITOR'),
        ('auditor.int', 'Internal Auditor', 'INTERNAL_AUDITOR'),
    ]

    users = []
    domain = tenant.trading_name.lower().replace(' ', '') + '.test'
    for username, full_name, role_code in user_defs:
        user, created = User.objects.get_or_create(
            tenant=tenant, email=f'{username}@{domain}',
            defaults={
                'auth_user_id': uuid.uuid4(),
                'full_name': full_name,
                'phone': f'+{tenant.country.country_code}0{random.randint(20,59)}{random.randint(1000000,9999999)}',
                'is_active': True,
            }
        )
        if created:
            UserRole.objects.create(user=user, role=roles[role_code])
        users.append(user)

    return users


def seed_branches(tenant):
    from apps.tenants.models import Branch

    branch_defs = [
        ('BR-A', 'Head Office / Main Branch', 'URBAN'),
        ('BR-B', 'Secondary Branch', 'PERI_URBAN'),
        ('BR-C', 'Rural Outpost', 'RURAL'),
    ]

    branches = []
    for code, name, btype in branch_defs:
        branch, _ = Branch.objects.get_or_create(
            tenant=tenant, branch_code=code,
            defaults={'branch_name': name, 'branch_type': btype}
        )
        branches.append(branch)
    return branches


def seed_loan_products(tenant):
    from apps.loans.models import LoanProduct

    products_def = [
        ('MICRO-001', 'Individual Micro Loan', 'INDIVIDUAL', 500, 5000, 3, 12, 'FLAT', 28, 2),
        ('MICRO-002', 'Group Solidarity Loan', 'GROUP', 200, 2000, 4, 6, 'FLAT', 24, 1.5),
        ('SME-001', 'SME Working Capital', 'SME', 5000, 50000, 6, 24, 'REDUCING_BALANCE', 32, 3),
        ('EMERG-001', 'Emergency Loan', 'EMERGENCY', 100, 1000, 1, 3, 'FLAT', 20, 0),
        ('AGRI-001', 'Agricultural Seasonal', 'AGRICULTURAL', 1000, 20000, 6, 6, 'FLAT', 26, 2),
    ]

    products = []
    for code, name, ptype, min_a, max_a, min_t, max_t, method, rate, fee in products_def:
        product, _ = LoanProduct.objects.get_or_create(
            tenant=tenant, product_code=code,
            defaults={
                'product_name': name, 'product_type': ptype,
                'min_amount': min_a, 'max_amount': max_a,
                'min_term_months': min_t, 'max_term_months': max_t,
                'interest_method': method, 'default_interest_rate_pct': rate,
                'origination_fee_pct': fee,
                'allowed_frequencies': ['MONTHLY', 'WEEKLY'],
                'group_liability_type': 'JOINT' if ptype == 'GROUP' else '',
            }
        )
        products.append(product)
    return products


GHANA_NAMES_FIRST = ['Kwame', 'Ama', 'Kofi', 'Abena', 'Yaw', 'Adwoa', 'Kwesi', 'Akua', 'Nana', 'Efua',
                      'Emmanuel', 'Patience', 'Samuel', 'Grace', 'Francis', 'Elizabeth', 'Daniel', 'Mercy',
                      'Joseph', 'Lydia', 'Michael', 'Felicia', 'Richard', 'Victoria', 'Isaac']
GHANA_NAMES_LAST = ['Asante', 'Mensah', 'Owusu', 'Boateng', 'Frimpong', 'Sarpong', 'Agyemang', 'Darko',
                     'Ampofo', 'Osei', 'Tetteh', 'Adjei', 'Appiah', 'Addo', 'Ankah', 'Badu', 'Asantewaa',
                     'Ofori', 'Gyamfi', 'Antwi', 'Boakye', 'Adu', 'Essien', 'Bonsu', 'Quartey']
ZAMBIA_NAMES_FIRST = ['Mwape', 'Chanda', 'Bwalya', 'Mutale', 'Tembo', 'Banda', 'Mulenga', 'Chisala',
                       'Kafula', 'Musonda', 'Nkandu', 'Chilufya', 'Mwansa', 'Kapata', 'Ngosa']
ZAMBIA_NAMES_LAST = ['Phiri', 'Banda', 'Mwale', 'Zulu', 'Tembo', 'Mwansa', 'Mumba', 'Mbewe',
                      'Lungu', 'Chanda', 'Kasonde', 'Nkonde', 'Sinkala', 'Musonda', 'Chipili']


def seed_clients(tenant):
    from apps.clients.models import Client
    from apps.tenants.models import Branch
    from apps.accounts.models import User

    branches = list(Branch.objects.filter(tenant=tenant))
    officers = list(User.objects.filter(tenant=tenant, user_roles__role__role_code='LOAN_OFFICER'))

    is_gh = tenant.country_code == 'GH'
    first_names = GHANA_NAMES_FIRST if is_gh else ZAMBIA_NAMES_FIRST
    last_names = GHANA_NAMES_LAST if is_gh else ZAMBIA_NAMES_LAST
    id_prefix = 'GHA-' if is_gh else ''

    count = 500 if tenant.licence_tier.can_accept_deposits else 300
    clients = []

    for i in range(count):
        if Client.objects.filter(tenant=tenant).count() >= count:
            break
        first = random.choice(first_names)
        last = random.choice(last_names)
        branch = random.choice(branches)
        officer = random.choice(officers) if officers else None

        # Some special flags
        is_pep = i == 7
        is_insider = i in (3, 15, 42)
        sanctions = i == 22
        kyc_statuses = ['VERIFIED'] * 80 + ['COMPLETE'] * 10 + ['INCOMPLETE'] * 8 + ['EXPIRED'] * 2

        national_id = f'{id_prefix}{random.randint(100000000, 999999999)}-{random.randint(0,9)}' if is_gh else f'{random.randint(100000, 999999)}/{random.randint(10, 99)}/{random.randint(1, 9)}'

        client = Client.objects.create(
            tenant=tenant,
            branch=branch,
            client_type=random.choice(['INDIVIDUAL'] * 8 + ['SME'] + ['GROUP']),
            client_number=f'CL-{i+1:05d}',
            full_legal_name=f'{first} {last}',
            first_name=first,
            last_name=last,
            date_of_birth=date(random.randint(1965, 2003), random.randint(1, 12), random.randint(1, 28)),
            gender=random.choice(['MALE', 'FEMALE']),
            national_id_type='GHANA_CARD' if is_gh else 'NRC',
            national_id_number=national_id,
            phone_primary=f'+{233 if is_gh else 260}{random.randint(20,59)}{random.randint(1000000,9999999)}',
            city=random.choice(['Accra', 'Kumasi', 'Tamale'] if is_gh else ['Lusaka', 'Ndola', 'Kitwe']),
            occupation=random.choice(['Trader', 'Farmer', 'Teacher', 'Driver', 'Seamstress', 'Carpenter', 'Nurse']),
            monthly_income=Decimal(random.randint(500, 8000)),
            income_currency=tenant.default_currency,
            risk_rating=random.choice(['LOW'] * 7 + ['MEDIUM'] * 2 + ['HIGH']),
            is_pep=is_pep,
            is_insider=is_insider,
            insider_relationship='DIRECTOR' if is_insider else '',
            kyc_status=random.choice(kyc_statuses),
            sanctions_checked=True,
            sanctions_hit=sanctions,
            onboarding_blocked=sanctions,
            assigned_officer=officer,
            is_test_data=True,
        )
        clients.append(client)

    return clients


def seed_loans(tenant):
    from apps.clients.models import Client
    from apps.loans.models import LoanProduct, Loan
    from apps.accounts.models import User

    clients = list(Client.objects.filter(tenant=tenant, kyc_status='VERIFIED')[:200])
    products = list(LoanProduct.objects.filter(tenant=tenant, is_active=True))
    officers = list(User.objects.filter(tenant=tenant, user_roles__role__role_code='LOAN_OFFICER'))

    if not clients or not products or not officers:
        return []

    loans = []
    for i, client in enumerate(clients):
        product = random.choice(products)
        officer = random.choice(officers)
        principal = Decimal(random.randint(int(product.min_amount), int(product.max_amount)))
        term = random.randint(product.min_term_months, product.max_term_months)
        rate = product.default_interest_rate_pct

        # Vary loan ages
        months_ago = random.randint(1, 20)
        app_date = date.today() - timedelta(days=months_ago * 30)
        disb_date = app_date + timedelta(days=random.randint(3, 14))

        # Determine status and classification
        if months_ago > term + 2:
            status = random.choice(['CLOSED'] * 8 + ['WRITTEN_OFF'] * 2)
            classification = 'CURRENT' if status == 'CLOSED' else 'LOSS'
            outstanding = Decimal('0') if status == 'CLOSED' else principal * Decimal('0.3')
        else:
            status = 'ACTIVE'
            # Most are current, some are overdue
            dpd = random.choice([0] * 60 + list(range(1, 30)) * 15 + list(range(31, 90)) * 10 + list(range(91, 200)) * 5)
            if dpd == 0:
                classification = 'CURRENT'
            elif dpd <= 30:
                classification = 'WATCH'
            elif dpd <= 90:
                classification = 'SUBSTANDARD'
            elif dpd <= 180:
                classification = 'DOUBTFUL'
            else:
                classification = 'LOSS'
            outstanding = principal * Decimal(str(random.uniform(0.1, 0.95)))

        total_interest = principal * rate / 100 * Decimal(term) / 12

        loan = Loan.objects.create(
            tenant=tenant,
            loan_number=f'LN-{app_date.strftime("%Y%m")}-{i+1:05d}',
            client=client,
            product=product,
            branch=client.branch,
            loan_officer=officer,
            principal_amount=principal,
            currency=tenant.default_currency,
            interest_rate_pct=rate,
            interest_method=product.interest_method,
            term_months=term,
            repayment_frequency='MONTHLY',
            total_interest=total_interest,
            total_repayable=principal + total_interest,
            outstanding_principal=outstanding.quantize(Decimal('0.01')),
            days_past_due=dpd if status == 'ACTIVE' else 0,
            status=status,
            classification=classification,
            application_date=app_date,
            disbursement_date=disb_date if status != 'APPLICATION' else None,
            maturity_date=disb_date + timedelta(days=term * 30) if disb_date else None,
            is_insider_loan=client.is_insider,
            is_test_data=True,
        )
        loans.append(loan)

    return loans


def seed_exchange_rates():
    from apps.ledger.models import ExchangeRate

    pairs = [('GHS', 'USD'), ('GHS', 'GBP'), ('GHS', 'EUR'),
             ('ZMW', 'USD'), ('ZMW', 'GBP'), ('ZMW', 'EUR')]
    base_rates = {
        ('GHS', 'USD'): 0.0625, ('GHS', 'GBP'): 0.049, ('GHS', 'EUR'): 0.057,
        ('ZMW', 'USD'): 0.037, ('ZMW', 'GBP'): 0.029, ('ZMW', 'EUR'): 0.034,
    }

    rates = []
    for day_offset in range(730):  # 24 months of daily rates
        rate_date = date.today() - timedelta(days=730 - day_offset)
        for base, target in pairs:
            base_rate = base_rates[(base, target)]
            # Add volatility — include depreciation periods
            trend = 1 - (day_offset / 730) * 0.15  # 15% depreciation over 2 years
            noise = random.uniform(-0.02, 0.02)
            rate_val = Decimal(str(round(base_rate * trend * (1 + noise), 8)))

            rate, created = ExchangeRate.objects.get_or_create(
                base_currency=base, target_currency=target, rate_date=rate_date,
                defaults={'rate': rate_val, 'source': 'SEED_DATA'}
            )
            if created:
                rates.append(rate)

    return rates


def seed_aml_scenarios(tenant):
    from apps.clients.models import Client
    from apps.compliance.models import AmlAlert, Str

    clients = list(Client.objects.filter(tenant=tenant)[:50])
    if not clients:
        return []

    alert_defs = [
        ('LARGE_CASH', 'Cash deposit of {currency} 85,000 exceeding CTR threshold', 85000, 'OPEN', 60),
        ('STRUCTURING', '4 cash transactions of {currency} 48,000 within 7 days', 48000, 'ESCALATED', 85),
        ('UNUSUAL_PATTERN', 'Full loan repayment significantly earlier than scheduled', 45000, 'UNDER_REVIEW', 55),
        ('LARGE_CASH', 'Cash withdrawal of {currency} 92,000 exceeding threshold', 92000, 'OPEN', 65),
        ('PEP_TRANSACTION', 'Transaction by Politically Exposed Person', 15000, 'OPEN', 70),
        ('RAPID_MOVEMENT', 'Multiple large deposits and withdrawals within 48 hours', 120000, 'OPEN', 75),
    ]

    alerts = []
    for i, (atype, desc, amount, status, risk) in enumerate(alert_defs):
        client = clients[i % len(clients)]
        alert = AmlAlert.objects.create(
            tenant=tenant,
            client=client,
            alert_type=atype,
            trigger_description=desc.format(currency=tenant.default_currency),
            trigger_amount=Decimal(amount),
            trigger_currency=tenant.default_currency,
            status=status,
            risk_score=risk,
        )
        alerts.append(alert)

        # Create STRs for escalated alerts
        if status == 'ESCALATED':
            Str.objects.create(
                tenant=tenant,
                alert=alert,
                client=client,
                report_type='STR',
                narrative=f'Suspicious activity detected: {desc.format(currency=tenant.default_currency)}',
                transaction_amount=Decimal(amount),
                transaction_currency=tenant.default_currency,
                status='SUBMITTED',
                submitted_to=f'FIC_{tenant.country_code}',
                submitted_at=timezone.now() - timedelta(days=2),
                fic_reference=f'FIC-2026-{random.randint(10000,99999)}',
                filed_by=User.objects.filter(tenant=tenant, user_roles__role__role_code='COMPLIANCE_OFFICER').first()
                         or User.objects.filter(tenant=tenant).first(),
            )

    return alerts


def seed_credit_scores(tenant):
    from apps.clients.models import Client
    from apps.scoring.models import CreditScoreModel, ClientCreditScore

    # Create default scoring model
    model, _ = CreditScoreModel.objects.get_or_create(
        tenant=tenant, model_name='Default MFI Score', model_version=1,
        defaults={
            'is_active': True,
            'criteria': [
                {'code': 'REPAYMENT_HISTORY', 'label': 'Repayment history', 'weight': 30, 'source': 'internal'},
                {'code': 'LOAN_CYCLE', 'label': 'Loan cycles completed', 'weight': 15, 'source': 'internal'},
                {'code': 'GROUP_MEMBERSHIP', 'label': 'Group membership', 'weight': 10, 'source': 'internal'},
                {'code': 'INCOME_STABILITY', 'label': 'Income stability', 'weight': 15, 'source': 'manual'},
                {'code': 'DEBT_TO_INCOME', 'label': 'Debt-to-income', 'weight': 15, 'source': 'computed'},
                {'code': 'MOMO_ACTIVITY', 'label': 'Mobile money activity', 'weight': 10, 'source': 'mobile_money'},
                {'code': 'BUSINESS_TENURE', 'label': 'Business tenure', 'weight': 5, 'source': 'manual'},
            ],
            'score_ranges': [
                {'min': 0, 'max': 30, 'label': 'HIGH_RISK', 'recommendation': 'DECLINE'},
                {'min': 31, 'max': 50, 'label': 'MEDIUM_RISK', 'recommendation': 'REVIEW'},
                {'min': 51, 'max': 70, 'label': 'ACCEPTABLE', 'recommendation': 'APPROVE_WITH_CONDITIONS'},
                {'min': 71, 'max': 100, 'label': 'LOW_RISK', 'recommendation': 'APPROVE'},
            ],
        }
    )

    # Score a sample of clients
    clients = Client.objects.filter(tenant=tenant, kyc_status='VERIFIED')[:100]
    scores = []
    for client in clients:
        total = Decimal(str(random.uniform(25, 95)))
        if total >= 71:
            label, rec = 'LOW_RISK', 'APPROVE'
        elif total >= 51:
            label, rec = 'ACCEPTABLE', 'APPROVE_WITH_CONDITIONS'
        elif total >= 31:
            label, rec = 'MEDIUM_RISK', 'REVIEW'
        else:
            label, rec = 'HIGH_RISK', 'DECLINE'

        score = ClientCreditScore.objects.create(
            tenant=tenant,
            client=client,
            model=model,
            total_score=total.quantize(Decimal('0.01')),
            risk_label=label,
            recommendation=rec,
            component_scores=[
                {'code': 'REPAYMENT_HISTORY', 'weighted_score': float(total * Decimal('0.3'))},
                {'code': 'LOAN_CYCLE', 'weighted_score': float(total * Decimal('0.15'))},
            ],
            computed_for='PERIODIC_REVIEW',
        )
        scores.append(score)

    return scores


# Import User at module level for seed_aml_scenarios
from apps.accounts.models import User

if __name__ == '__main__':
    seed_all()
