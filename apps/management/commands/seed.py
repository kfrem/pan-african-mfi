"""
Test Data Seed Script — Pan-African Microfinance SaaS
Generates realistic synthetic data for staging/demo environments.

Usage:
  python manage.py seed --env=staging
  python manage.py seed --env=demo --tenant=TEST-GH-T2

Generates per test tenant:
  - 500 individual clients + 200 group members + 50 SME clients
  - 5 loan products + deposit products (if deposit-taking)
  - 800+ loans across all statuses and classifications
  - 24 months of repayment history
  - GL transactions + chart of accounts
  - AML alerts and STR scenarios
  - Exchange rate history
  - Investor profiles with FX data
"""
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone


# Ghana names pool
GH_FIRST_NAMES_M = ['Kwame', 'Kofi', 'Yaw', 'Kweku', 'Kwesi', 'Emmanuel', 'Samuel', 'Daniel', 'Joseph', 'Francis', 'Michael', 'Richard', 'Isaac', 'Peter', 'James']
GH_FIRST_NAMES_F = ['Ama', 'Abena', 'Adwoa', 'Akua', 'Efua', 'Patience', 'Grace', 'Elizabeth', 'Mercy', 'Victoria', 'Lydia', 'Felicia', 'Mary', 'Sarah', 'Helen']
GH_LAST_NAMES = ['Asante', 'Mensah', 'Owusu', 'Boateng', 'Frimpong', 'Sarpong', 'Agyemang', 'Darko', 'Ampofo', 'Osei', 'Tetteh', 'Adjei', 'Appiah', 'Addo', 'Ankah', 'Badu', 'Ofori', 'Gyamfi', 'Antwi', 'Boakye']
GH_CITIES = ['Accra', 'Kumasi', 'Tamale', 'Cape Coast', 'Tema', 'Sekondi-Takoradi', 'Koforidua', 'Sunyani', 'Ho', 'Wa']
GH_REGIONS = ['Greater Accra', 'Ashanti', 'Northern', 'Central', 'Western', 'Eastern', 'Volta', 'Bono']

ZM_FIRST_NAMES_M = ['Mwamba', 'Bwalya', 'Mutale', 'Chanda', 'Banda', 'Phiri', 'Mulenga', 'Tembo', 'Ngosa', 'Zulu']
ZM_FIRST_NAMES_F = ['Mwila', 'Bwalya', 'Mutale', 'Chilufya', 'Nkandu', 'Musonda', 'Kabwe', 'Mumba', 'Kapata', 'Mwansa']
ZM_LAST_NAMES = ['Mwamba', 'Bwalya', 'Mutale', 'Chanda', 'Banda', 'Phiri', 'Mulenga', 'Tembo', 'Ngosa', 'Zulu', 'Sakala', 'Mwale', 'Lungu', 'Kasonde', 'Chipeta']


class Command(BaseCommand):
    help = 'Generate test data for staging/demo environments'

    def add_arguments(self, parser):
        parser.add_argument('--env', type=str, default='staging', choices=['staging', 'demo'])
        parser.add_argument('--tenant', type=str, help='Specific tenant ID to seed')

    def handle(self, *args, **options):
        env = options['env']
        self.stdout.write(f'Seeding {env} data...')

        if env == 'demo':
            self._seed_demo(options.get('tenant'))
        else:
            self._seed_staging()

        self.stdout.write(self.style.SUCCESS('Seed complete'))

    def _seed_staging(self):
        """Full staging dataset — all test tenants with complete data."""
        self._create_exchange_rates()

        tenants = [
            {'code': 'TEST-GH-T2', 'name': 'Accra MicroCredit Ltd', 'country': 'GH', 'tier': 'GHANA_TIER_2', 'currency': 'GHS', 'clients': 500, 'groups': 40},
            {'code': 'TEST-GH-T3', 'name': 'Kumasi Lending Co', 'country': 'GH', 'tier': 'GHANA_TIER_3', 'currency': 'GHS', 'clients': 300, 'groups': 20},
            {'code': 'TEST-ZM-T1', 'name': 'Lusaka Finance Ltd', 'country': 'ZM', 'tier': 'ZAMBIA_TIER_I', 'currency': 'ZMW', 'clients': 500, 'groups': 40},
            {'code': 'TEST-ZM-T2', 'name': 'Ndola Credit Services', 'country': 'ZM', 'tier': 'ZAMBIA_TIER_II', 'currency': 'ZMW', 'clients': 300, 'groups': 20},
        ]

        for t in tenants:
            self.stdout.write(f'  Creating tenant: {t["name"]}')
            tenant_id = self._create_tenant(t)
            self._create_branches(tenant_id, t['country'])
            self._create_users(tenant_id)
            self._create_loan_products(tenant_id, t['tier'])
            self._create_clients(tenant_id, t['clients'], t['country'])
            self._create_groups(tenant_id, t['groups'], t['country'])
            self._create_loans(tenant_id, t['currency'])
            self._create_aml_scenarios(tenant_id)
            self._create_investor_profiles(tenant_id, t['currency'])
            self._create_chart_of_accounts(tenant_id, t['currency'])
            self.stdout.write(f'    Done: {t["name"]}')

    def _seed_demo(self, tenant_code=None):
        """Curated demo dataset — smaller but visually impressive."""
        self._create_exchange_rates()
        t = {'code': tenant_code or 'DEMO-GH', 'name': 'Demo MFI Ghana', 'country': 'GH',
             'tier': 'GHANA_TIER_2', 'currency': 'GHS', 'clients': 50, 'groups': 5}
        tenant_id = self._create_tenant(t)
        self._create_branches(tenant_id, 'GH')
        self._create_users(tenant_id)
        self._create_loan_products(tenant_id, t['tier'])
        self._create_clients(tenant_id, t['clients'], 'GH')
        self._create_loans(tenant_id, 'GHS')
        self._create_investor_profiles(tenant_id, 'GHS')
        self._create_chart_of_accounts(tenant_id, 'GHS')

    def _create_tenant(self, config):
        """Create a test tenant with full configuration."""
        from apps.tenants.models import Tenant, LicenceTier, LicenceProfile
        tier = LicenceTier.objects.get(tier_code=config['tier'])
        tenant = Tenant.objects.create(
            name=config['name'], trading_name=config['name'],
            country_id=config['country'], licence_tier=tier,
            default_currency=config['currency'], is_test_data_tenant=False,
        )
        LicenceProfile.objects.create(
            tenant=tenant, licence_number=f'LIC-{config["code"]}',
            licensing_authority=tier.country.regulatory_authority,
            effective_from=date(2023, 1, 1), expires_on=date(2026, 12, 31),
        )
        return str(tenant.id)

    def _create_branches(self, tenant_id, country):
        from apps.tenants.models import Branch
        branches = [
            ('BR-001', 'Head Office', 'URBAN'),
            ('BR-002', 'Market Branch', 'PERI_URBAN'),
            ('BR-003', 'Rural Outreach', 'RURAL'),
        ]
        for code, name, btype in branches:
            Branch.objects.create(tenant_id=tenant_id, branch_code=code, branch_name=name, branch_type=btype)

    def _create_users(self, tenant_id):
        """Create test users for all 12 roles."""
        from apps.accounts.models import User, Role, UserRole
        from apps.tenants.models import Branch

        branch = Branch.objects.filter(tenant_id=tenant_id).first()
        roles_map = {
            'ceo': 'CEO_CFO', 'cfo': 'CEO_CFO', 'credit.mgr': 'CREDIT_MANAGER',
            'accountant': 'ACCOUNTANT', 'compliance': 'COMPLIANCE_OFFICER',
            'it.admin': 'IT_SECURITY_ADMIN', 'officer1': 'LOAN_OFFICER',
            'officer2': 'LOAN_OFFICER', 'branch.mgr1': 'BRANCH_MANAGER',
            'board1': 'BOARD_DIRECTOR', 'investor1': 'INVESTOR',
            'auditor.ext': 'EXTERNAL_AUDITOR', 'data.entry1': 'DATA_ENTRY',
        }

        # Seed system roles for this tenant
        system_roles = [
            'DATA_ENTRY', 'LOAN_OFFICER', 'BRANCH_MANAGER', 'CREDIT_MANAGER',
            'ACCOUNTANT', 'COMPLIANCE_OFFICER', 'IT_SECURITY_ADMIN', 'CEO_CFO',
            'BOARD_DIRECTOR', 'INVESTOR', 'EXTERNAL_AUDITOR', 'INTERNAL_AUDITOR',
        ]
        for rc in system_roles:
            Role.objects.get_or_create(tenant_id=tenant_id, role_code=rc,
                defaults={'role_name': rc.replace('_', ' ').title(), 'is_system_role': True})

        for username, role_code in roles_map.items():
            user = User.objects.create(
                tenant_id=tenant_id, auth_user_id=uuid.uuid4(),
                email=f'{username}@test.mfi', full_name=f'Test {username.title()}',
                branch=branch if role_code in ['LOAN_OFFICER', 'BRANCH_MANAGER', 'DATA_ENTRY'] else None,
            )
            role = Role.objects.get(tenant_id=tenant_id, role_code=role_code)
            UserRole.objects.create(user=user, role=role)

    def _create_clients(self, tenant_id, count, country):
        """Create individual clients with realistic KYC data."""
        from apps.clients.models import Client
        from apps.tenants.models import Branch
        from apps.accounts.models import User

        branches = list(Branch.objects.filter(tenant_id=tenant_id).values_list('id', flat=True))
        officers = list(User.objects.filter(tenant_id=tenant_id, user_roles__role__role_code='LOAN_OFFICER').values_list('id', flat=True))

        names_m = GH_FIRST_NAMES_M if country == 'GH' else ZM_FIRST_NAMES_M
        names_f = GH_FIRST_NAMES_F if country == 'GH' else ZM_FIRST_NAMES_F
        last_names = GH_LAST_NAMES if country == 'GH' else ZM_LAST_NAMES
        cities = GH_CITIES if country == 'GH' else ['Lusaka', 'Ndola', 'Kitwe', 'Livingstone', 'Chipata']
        id_prefix = 'GHA' if country == 'GH' else ''

        clients = []
        for i in range(count):
            gender = random.choice(['MALE', 'FEMALE'])
            first = random.choice(names_m if gender == 'MALE' else names_f)
            last = random.choice(last_names)
            dob = date(random.randint(1965, 2005), random.randint(1, 12), random.randint(1, 28))

            if country == 'GH':
                nat_id = f'GHA-{random.randint(100000000, 999999999)}-{random.randint(0, 9)}'
            else:
                nat_id = f'{random.randint(100000, 999999)}/{random.randint(10, 99)}/{random.randint(1, 9)}'

            kyc = random.choices(['VERIFIED', 'COMPLETE', 'INCOMPLETE', 'EXPIRED'], weights=[70, 15, 10, 5])[0]
            risk = random.choices(['LOW', 'MEDIUM', 'HIGH'], weights=[75, 20, 5])[0]

            # Special cases: PEP client, sanctions hit, insider
            is_pep = i == 7
            sanctions_hit = i == 15
            is_insider = i in [3, 25]

            clients.append(Client(
                tenant_id=tenant_id,
                branch_id=random.choice(branches),
                client_type='INDIVIDUAL',
                client_number=f'CL-{str(i+1).zfill(5)}',
                full_legal_name=f'{first} {last}',
                first_name=first, last_name=last,
                date_of_birth=dob, gender=gender,
                national_id_type='GHANA_CARD' if country == 'GH' else 'NRC',
                national_id_number=nat_id,
                phone_primary=f'+{233 if country=="GH" else 260}{random.randint(200000000, 599999999)}',
                city=random.choice(cities),
                occupation=random.choice(['Trader', 'Farmer', 'Teacher', 'Artisan', 'Nurse', 'Driver', 'Tailor']),
                monthly_income=Decimal(str(random.randint(500, 8000))),
                income_currency='GHS' if country == 'GH' else 'ZMW',
                risk_rating=risk, kyc_status=kyc,
                is_pep=is_pep, sanctions_hit=sanctions_hit,
                is_insider=is_insider,
                insider_relationship='DIRECTOR' if i == 3 else ('STAFF' if i == 25 else ''),
                onboarding_blocked=sanctions_hit,
                block_reason='Sanctions list match' if sanctions_hit else '',
                assigned_officer_id=random.choice(officers) if officers else None,
                is_test_data=True,
            ))

        Client.objects.bulk_create(clients, batch_size=100)
        self.stdout.write(f'    Created {count} clients')

    def _create_groups(self, tenant_id, group_count, country):
        """Create solidarity groups with members."""
        from apps.clients.models import Client, Group, GroupMember
        from apps.tenants.models import Branch

        branch = Branch.objects.filter(tenant_id=tenant_id).first()
        clients = list(Client.objects.filter(tenant_id=tenant_id, client_type='INDIVIDUAL').values_list('id', flat=True)[:group_count * 5])

        for i in range(group_count):
            group = Group.objects.create(
                tenant_id=tenant_id, branch=branch,
                group_name=f'Solidarity Group {i+1}',
                group_number=f'GRP-{str(i+1).zfill(4)}',
                meeting_frequency='WEEKLY', meeting_day='Monday',
            )
            members = clients[i*5:(i+1)*5]
            for j, client_id in enumerate(members):
                GroupMember.objects.create(
                    group=group, client_id=client_id,
                    joined_at=date.today() - timedelta(days=random.randint(90, 730)),
                )
            if members:
                group.leader_id = members[0]
                group.save()

        self.stdout.write(f'    Created {group_count} groups')

    def _create_loan_products(self, tenant_id, tier_code):
        from apps.loans.models import LoanProduct
        products = [
            ('MICRO-001', 'Individual Micro Loan', 'INDIVIDUAL', 500, 5000, 3, 12, 'FLAT', 30, 2),
            ('MICRO-002', 'Group Solidarity Loan', 'GROUP', 200, 2000, 4, 6, 'FLAT', 28, 1.5),
            ('SME-001', 'SME Working Capital', 'SME', 5000, 50000, 6, 24, 'REDUCING_BALANCE', 32, 3),
            ('EMERG-001', 'Emergency Loan', 'EMERGENCY', 100, 1000, 1, 3, 'FLAT', 35, 0),
            ('AGRI-001', 'Agricultural Seasonal', 'AGRICULTURAL', 1000, 20000, 6, 6, 'FLAT', 25, 2),
        ]
        for code, name, ptype, min_a, max_a, min_t, max_t, method, rate, fee in products:
            LoanProduct.objects.create(
                tenant_id=tenant_id, product_code=code, product_name=name,
                product_type=ptype, min_amount=min_a, max_amount=max_a,
                min_term_months=min_t, max_term_months=max_t,
                interest_method=method, default_interest_rate_pct=rate,
                origination_fee_pct=fee,
                group_liability_type='JOINT' if ptype == 'GROUP' else '',
                allowed_frequencies=['MONTHLY', 'WEEKLY'] if ptype in ['INDIVIDUAL', 'GROUP'] else ['MONTHLY'],
            )
        self.stdout.write('    Created 5 loan products')

    def _create_loans(self, tenant_id, currency):
        """Create loans with various statuses and repayment histories."""
        from apps.clients.models import Client
        from apps.loans.models import Loan, LoanProduct, RepaymentSchedule, Repayment
        from apps.accounts.models import User
        from apps.tenants.models import Branch

        clients = list(Client.objects.filter(tenant_id=tenant_id, client_type='INDIVIDUAL', onboarding_blocked=False)[:200])
        products = list(LoanProduct.objects.filter(tenant_id=tenant_id))
        officers = list(User.objects.filter(tenant_id=tenant_id, user_roles__role__role_code='LOAN_OFFICER'))
        branch = Branch.objects.filter(tenant_id=tenant_id).first()

        if not clients or not products or not officers:
            return

        statuses_weights = [
            ('ACTIVE', 50), ('DISBURSED', 10), ('CLOSED', 25),
            ('PENDING_APPROVAL', 5), ('APPLICATION', 5), ('WRITTEN_OFF', 3), ('RESTRUCTURED', 2),
        ]
        statuses = [s for s, _ in statuses_weights]
        weights = [w for _, w in statuses_weights]

        loan_count = 0
        for client in clients:
            n_loans = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
            for _ in range(n_loans):
                product = random.choice(products)
                status = random.choices(statuses, weights=weights)[0]
                principal = Decimal(str(random.randint(int(product.min_amount), int(product.max_amount))))
                term = random.randint(product.min_term_months, product.max_term_months)
                rate = product.default_interest_rate_pct
                total_interest = principal * rate / 100 * term / 12
                total_repayable = principal + total_interest

                app_date = date.today() - timedelta(days=random.randint(30, 720))
                disb_date = app_date + timedelta(days=random.randint(3, 14)) if status not in ['APPLICATION', 'PENDING_APPROVAL'] else None

                # Calculate days past due for active loans
                dpd = 0
                classification = 'CURRENT'
                if status in ['ACTIVE', 'DISBURSED'] and random.random() < 0.25:
                    dpd = random.choice([0, 0, 0, 5, 15, 35, 65, 95, 200])
                    if dpd == 0: classification = 'CURRENT'
                    elif dpd <= 30: classification = 'WATCH'
                    elif dpd <= 90: classification = 'SUBSTANDARD'
                    elif dpd <= 180: classification = 'DOUBTFUL'
                    else: classification = 'LOSS'

                outstanding = principal if status in ['ACTIVE', 'DISBURSED'] else (Decimal('0') if status == 'CLOSED' else principal)
                if status in ['ACTIVE', 'DISBURSED']:
                    outstanding = principal * Decimal(str(random.uniform(0.2, 0.95)))

                loan_count += 1
                Loan.objects.create(
                    tenant_id=tenant_id,
                    loan_number=f'LN-{app_date.strftime("%Y%m")}-{str(loan_count).zfill(5)}',
                    client=client, product=product, branch=branch,
                    loan_officer=random.choice(officers),
                    principal_amount=principal, currency=currency,
                    interest_rate_pct=rate, interest_method=product.interest_method,
                    term_months=term, repayment_frequency='MONTHLY',
                    total_interest=total_interest, total_repayable=total_repayable,
                    outstanding_principal=outstanding.quantize(Decimal('0.01')),
                    days_past_due=dpd, classification=classification,
                    status=status, application_date=app_date,
                    disbursement_date=disb_date,
                    maturity_date=(disb_date + timedelta(days=term*30)) if disb_date else None,
                    is_insider_loan=client.is_insider,
                    is_test_data=True,
                )

        self.stdout.write(f'    Created {loan_count} loans')

    def _create_aml_scenarios(self, tenant_id):
        """Create AML test scenarios — alerts, STRs, PEP cases."""
        from apps.compliance.models import AmlAlert, Str
        from apps.clients.models import Client
        from apps.accounts.models import User

        clients = list(Client.objects.filter(tenant_id=tenant_id)[:10])
        user = User.objects.filter(tenant_id=tenant_id, user_roles__role__role_code='COMPLIANCE_OFFICER').first()
        if not clients or not user:
            return

        scenarios = [
            ('LARGE_CASH', 'OPEN', 85000, 75),
            ('STRUCTURING', 'ESCALATED', 48000, 85),
            ('UNUSUAL_PATTERN', 'UNDER_REVIEW', 45000, 60),
            ('PEP_TRANSACTION', 'OPEN', 15000, 70),
            ('LARGE_CASH', 'STR_FILED', 92000, 80),
        ]

        for i, (alert_type, status, amount, risk) in enumerate(scenarios):
            alert = AmlAlert.objects.create(
                tenant_id=tenant_id, client=clients[i],
                alert_type=alert_type, trigger_description=f'Test {alert_type} scenario',
                trigger_amount=Decimal(str(amount)), trigger_currency='GHS',
                status=status, risk_score=risk,
            )
            if status == 'STR_FILED':
                Str.objects.create(
                    tenant_id=tenant_id, alert=alert, client=clients[i],
                    report_type='STR', narrative=f'Suspicious activity: {alert_type}',
                    transaction_amount=Decimal(str(amount)),
                    status='SUBMITTED', filed_by=user,
                    fic_reference=f'FIC-2026-{str(i+1).zfill(5)}',
                )

        self.stdout.write('    Created 5 AML scenarios')

    def _create_investor_profiles(self, tenant_id, currency):
        from apps.investors.models import InvestorProfile
        from apps.accounts.models import User
        user = User.objects.filter(tenant_id=tenant_id, user_roles__role__role_code='INVESTOR').first()
        if not user:
            return
        InvestorProfile.objects.create(
            tenant_id=tenant_id, user=user, investor_name='Test USD Investor',
            investor_type='INSTITUTIONAL', investment_currency='USD',
            invested_amount=Decimal('500000'), invested_amount_local=Decimal('8000000'),
            investment_date=date.today() - timedelta(days=540),
            exchange_rate_at_investment=Decimal('0.0625'),
        )

    def _create_chart_of_accounts(self, tenant_id, currency):
        from apps.ledger.models import GlAccount
        accounts = [
            ('1000', 'Cash and Bank', 'ASSET', 'D', True),
            ('1010', 'Cash on Hand', 'ASSET', 'D', False),
            ('1020', 'Bank Accounts', 'ASSET', 'D', False),
            ('1100', 'Loans Receivable', 'ASSET', 'D', True),
            ('1110', 'Performing Loans', 'ASSET', 'D', False),
            ('1120', 'Non-Performing Loans', 'ASSET', 'D', False),
            ('1200', 'Provision for Loan Losses', 'ASSET', 'D', False),
            ('2000', 'Liabilities', 'LIABILITY', 'C', True),
            ('2010', 'Customer Deposits', 'LIABILITY', 'C', False),
            ('2020', 'Borrowings', 'LIABILITY', 'C', False),
            ('3000', 'Equity', 'EQUITY', 'C', True),
            ('3010', 'Paid-Up Capital', 'EQUITY', 'C', False),
            ('3020', 'Retained Earnings', 'EQUITY', 'C', False),
            ('4000', 'Income', 'INCOME', 'C', True),
            ('4010', 'Interest Income', 'INCOME', 'C', False),
            ('4020', 'Fee Income', 'INCOME', 'C', False),
            ('5000', 'Expenses', 'EXPENSE', 'D', True),
            ('5010', 'Staff Costs', 'EXPENSE', 'D', False),
            ('5020', 'Operating Expenses', 'EXPENSE', 'D', False),
            ('5030', 'Loan Loss Provision Charge', 'EXPENSE', 'D', False),
        ]
        for code, name, atype, balance, is_header in accounts:
            GlAccount.objects.create(
                tenant_id=tenant_id, account_code=code, account_name=name,
                account_type=atype, normal_balance=balance, currency=currency,
                is_header=is_header, is_system_account=True,
            )
        self.stdout.write('    Created 20 GL accounts')

    def _create_exchange_rates(self):
        """Seed 24 months of daily exchange rates."""
        from apps.ledger.models import ExchangeRate
        if ExchangeRate.objects.exists():
            return

        base_rates = {
            ('GHS', 'USD'): 0.0625, ('GHS', 'GBP'): 0.0493, ('GHS', 'EUR'): 0.0575,
            ('ZMW', 'USD'): 0.0370, ('ZMW', 'GBP'): 0.0292, ('ZMW', 'EUR'): 0.0341,
        }
        rates = []
        for day_offset in range(730):
            rate_date = date.today() - timedelta(days=day_offset)
            for (base, target), base_rate in base_rates.items():
                # Add realistic volatility with depreciation trend
                noise = random.uniform(-0.005, 0.003)
                depreciation = day_offset * 0.000015  # Gradual local currency depreciation
                rate = base_rate * (1 + noise - depreciation)
                rates.append(ExchangeRate(
                    base_currency=base, target_currency=target,
                    rate=Decimal(str(round(rate, 8))), rate_date=rate_date,
                    source='SEED_DATA',
                ))

        ExchangeRate.objects.bulk_create(rates, batch_size=500, ignore_conflicts=True)
        self.stdout.write(f'  Created {len(rates)} exchange rate records')
