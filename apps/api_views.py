"""
REST API Views — Pan-African Microfinance SaaS
Core CRUD endpoints with tenant isolation, RBAC, and offline sync support.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.tenants.models import Tenant, CountryPack, LicenceTier, Branch
from apps.accounts.models import User, Role
from apps.clients.models import Client, Group, KycDocument
from apps.loans.models import LoanProduct, Loan, RepaymentSchedule, Repayment
from apps.api_serializers import (
    TenantSerializer, CountryPackSerializer, LicenceTierSerializer, BranchSerializer,
    UserSerializer, UserCreateSerializer, RoleSerializer,
    ClientListSerializer, ClientDetailSerializer, GroupSerializer, KycDocumentSerializer,
    LoanProductSerializer, LoanListSerializer, LoanDetailSerializer,
    LoanApplicationSerializer, RepaymentSerializer, RepaymentCaptureSerializer,
    DepositProductSerializer, DepositAccountSerializer, DepositTransactionSerializer,
    InvestorProfileSerializer, InvestorShareLinkSerializer,
    AmlAlertSerializer, PrudentialReturnSerializer,
    MobileMoneyProviderSerializer, MobileMoneyTransactionSerializer,
    CollectRepaymentSerializer, DisburseLoanSerializer,
    ReportDefinitionSerializer, ReportRunSerializer, RequestReportSerializer,
    ImportJobSerializer,
)


# ─── PERMISSION HELPERS ───

class HasPermission:
    """Check if user has a specific permission via their roles."""
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def __call__(self):
        return type(f'Has_{self.permission_code}', (permissions.BasePermission,), {
            'has_permission': lambda self_inner, request, view: (
                request.user and
                hasattr(request, 'tenant_id') and
                User.objects.filter(
                    auth_user_id=request.supabase_user_id,
                    user_roles__role__role_permissions__permission__permission_code=self.permission_code
                ).exists()
            )
        })()


class TenantScopedMixin:
    """Automatically filter querysets by tenant and inject tenant on create."""

    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id:
            return qs.filter(tenant_id=tenant_id)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


# ─── REFERENCE DATA (global, read-only) ───

class CountryPackViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CountryPack.objects.filter(is_active=True)
    serializer_class = CountryPackSerializer


class LicenceTierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LicenceTier.objects.all()
    serializer_class = LicenceTierSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country_code=country)
        return qs


# ─── TENANT MANAGEMENT ───

class TenantViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    def get_queryset(self):
        # Tenants see only their own tenant
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id)
        return Tenant.objects.none()


class BranchViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer


# ─── USERS ───

class UserViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = User.objects.filter(deleted_at__isnull=True)
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        try:
            user = User.objects.get(
                auth_user_id=request.supabase_user_id,
                tenant_id=request.tenant_id
            )
            return Response(UserSerializer(user).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class RoleViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


# ─── CLIENTS ───

class ClientViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Client.objects.filter(deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        return ClientDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filters
        branch = self.request.query_params.get('branch')
        if branch:
            qs = qs.filter(branch_id=branch)
        kyc = self.request.query_params.get('kyc_status')
        if kyc:
            qs = qs.filter(kyc_status=kyc)
        officer = self.request.query_params.get('officer')
        if officer:
            qs = qs.filter(assigned_officer_id=officer)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(full_legal_name__icontains=search) |
                Q(client_number__icontains=search) |
                Q(national_id_number__icontains=search) |
                Q(phone_primary__icontains=search)
            )
        return qs.select_related('branch', 'assigned_officer')

    @action(detail=True, methods=['post'])
    def verify_kyc(self, request, pk=None):
        """Mark a client's KYC as verified."""
        client = self.get_object()
        user = User.objects.get(auth_user_id=request.supabase_user_id)
        client.kyc_status = 'VERIFIED'
        client.kyc_verified_by = user
        client.kyc_verified_at = timezone.now()
        client.save()
        return Response(ClientDetailSerializer(client).data)

    @action(detail=False, methods=['post'])
    def sync_batch(self, request):
        """Accept a batch of offline-created clients."""
        records = request.data.get('records', [])
        results = {'created': 0, 'conflicts': 0, 'errors': []}
        for record in records:
            try:
                sync_id = record.get('sync_id')
                if Client.objects.filter(sync_id=sync_id).exists():
                    results['conflicts'] += 1
                    continue
                serializer = ClientDetailSerializer(data=record, context={'request': request})
                if serializer.is_valid():
                    serializer.save(
                        tenant_id=request.tenant_id,
                        sync_status='SYNCED',
                        server_confirmed_at=timezone.now()
                    )
                    results['created'] += 1
                else:
                    results['errors'].append({'sync_id': sync_id, 'errors': serializer.errors})
            except Exception as e:
                results['errors'].append({'sync_id': record.get('sync_id'), 'error': str(e)})
        return Response(results)


class GroupViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Group.objects.filter(is_active=True)
    serializer_class = GroupSerializer


class KycDocumentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = KycDocument.objects.all()
    serializer_class = KycDocumentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        client = self.request.query_params.get('client')
        if client:
            qs = qs.filter(client_id=client)
        return qs

    def perform_create(self, serializer):
        user = User.objects.get(auth_user_id=self.request.supabase_user_id)
        serializer.save(tenant_id=self.request.tenant_id, uploaded_by=user)


# ─── LOANS ───

class LoanProductViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = LoanProduct.objects.filter(is_active=True)
    serializer_class = LoanProductSerializer


class LoanViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Loan.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        if self.action == 'apply':
            return LoanApplicationSerializer
        return LoanDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        classification = self.request.query_params.get('classification')
        if classification:
            qs = qs.filter(classification=classification)
        client = self.request.query_params.get('client')
        if client:
            qs = qs.filter(client_id=client)
        branch = self.request.query_params.get('branch')
        if branch:
            qs = qs.filter(branch_id=branch)
        officer = self.request.query_params.get('officer')
        if officer:
            qs = qs.filter(loan_officer_id=officer)
        return qs.select_related('client', 'product', 'loan_officer', 'branch')

    @action(detail=False, methods=['post'])
    def apply(self, request):
        """Submit a new loan application."""
        serializer = LoanApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        product = LoanProduct.objects.get(id=data['product_id'], tenant_id=request.tenant_id)
        client = Client.objects.get(id=data['client_id'], tenant_id=request.tenant_id)

        # Validate against product limits
        if data['principal_amount'] < product.min_amount:
            return Response({'error': f'Amount below minimum ({product.min_amount})'}, status=400)
        if data['principal_amount'] > product.max_amount:
            return Response({'error': f'Amount exceeds maximum ({product.max_amount})'}, status=400)
        if data['term_months'] < product.min_term_months:
            return Response({'error': f'Term below minimum ({product.min_term_months} months)'}, status=400)
        if data['term_months'] > product.max_term_months:
            return Response({'error': f'Term exceeds maximum ({product.max_term_months} months)'}, status=400)

        # Check insider loan
        is_insider = client.is_insider

        # Calculate interest and total
        rate = data.get('interest_rate_pct', product.default_interest_rate_pct)
        principal = data['principal_amount']
        term = data['term_months']

        if product.interest_method == 'FLAT':
            total_interest = principal * (rate / 100) * (term / 12)
        else:
            # Reducing balance approximation for display
            monthly_rate = rate / 100 / 12
            if monthly_rate > 0:
                payment = principal * (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
                total_interest = (payment * term) - principal
            else:
                total_interest = 0

        origination_fee = principal * (product.origination_fee_pct / 100)
        total_repayable = principal + total_interest + origination_fee

        # Generate loan number
        from datetime import date
        count = Loan.objects.filter(tenant_id=request.tenant_id).count() + 1
        loan_number = f"LN-{date.today().strftime('%Y%m')}-{count:05d}"

        loan = Loan.objects.create(
            tenant_id=request.tenant_id,
            loan_number=loan_number,
            client=client,
            product=product,
            branch_id=data['branch_id'],
            loan_officer=user,
            principal_amount=principal,
            currency=Tenant.objects.get(id=request.tenant_id).default_currency,
            interest_rate_pct=rate,
            interest_method=product.interest_method,
            term_months=term,
            repayment_frequency=data['repayment_frequency'],
            origination_fee=origination_fee,
            total_interest=total_interest,
            total_repayable=total_repayable,
            outstanding_principal=principal,
            application_date=date.today(),
            is_insider_loan=is_insider,
            collateral_description=data.get('collateral_description', ''),
            collateral_value=data.get('collateral_value'),
            guarantor_client_id=data.get('guarantor_client_id'),
            status='PENDING_APPROVAL',
        )

        return Response(LoanDetailSerializer(loan).data, status=201)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending loan application (checker action)."""
        loan = self.get_object()
        if loan.status != 'PENDING_APPROVAL':
            return Response({'error': f'Cannot approve loan in {loan.status} status'}, status=400)

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        if loan.loan_officer == user:
            return Response({'error': 'Maker-checker violation: loan officer cannot approve their own application'}, status=403)

        loan.status = 'APPROVED'
        loan.approval_date = timezone.now().date()
        loan.approved_by = user
        loan.save()
        return Response(LoanDetailSerializer(loan).data)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse an approved loan."""
        loan = self.get_object()
        if loan.status != 'APPROVED':
            return Response({'error': f'Cannot disburse loan in {loan.status} status'}, status=400)

        # KYC gate (also enforced by DB trigger)
        if loan.client.kyc_status == 'INCOMPLETE':
            return Response({'error': 'Cannot disburse: client KYC is INCOMPLETE'}, status=400)

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        today = timezone.now().date()

        loan.status = 'DISBURSED'
        loan.disbursement_date = today
        loan.disbursed_by = user
        loan.save()

        # Generate repayment schedule
        self._generate_schedule(loan)

        return Response(LoanDetailSerializer(loan).data)

    def _generate_schedule(self, loan):
        """Generate repayment schedule based on loan terms."""
        from datetime import timedelta
        from decimal import Decimal

        principal = loan.principal_amount
        rate = loan.interest_rate_pct
        term = loan.term_months
        freq = loan.repayment_frequency

        # Calculate period count and interval
        if freq == 'MONTHLY':
            periods = term
            interval_days = 30
        elif freq == 'WEEKLY':
            periods = term * 4
            interval_days = 7
        elif freq == 'FORTNIGHTLY':
            periods = term * 2
            interval_days = 14
        else:  # DAILY
            periods = term * 30
            interval_days = 1

        if loan.interest_method == 'FLAT':
            total_interest = principal * (rate / 100) * (Decimal(term) / 12)
            period_principal = principal / periods
            period_interest = total_interest / periods
        else:
            monthly_rate = rate / 100 / 12
            if monthly_rate > 0:
                # Convert to period rate
                if freq == 'MONTHLY':
                    period_rate = monthly_rate
                elif freq == 'WEEKLY':
                    period_rate = monthly_rate / 4
                elif freq == 'FORTNIGHTLY':
                    period_rate = monthly_rate / 2
                else:
                    period_rate = monthly_rate / 30

                payment = principal * (period_rate * (1 + period_rate)**periods) / ((1 + period_rate)**periods - 1)
            else:
                payment = principal / periods
                period_rate = Decimal(0)

        balance = principal
        start_date = loan.first_repayment_date or (loan.disbursement_date + timedelta(days=interval_days))

        schedules = []
        for i in range(1, periods + 1):
            due_date = start_date + timedelta(days=interval_days * (i - 1))

            if loan.interest_method == 'FLAT':
                p_due = round(period_principal, 4)
                i_due = round(period_interest, 4)
            else:
                i_due = round(balance * period_rate, 4)
                p_due = round(payment - i_due, 4)

            # Last instalment: clean up rounding
            if i == periods:
                p_due = balance

            balance = max(balance - p_due, Decimal(0))

            schedules.append(RepaymentSchedule(
                tenant_id=loan.tenant_id,
                loan_id=loan.id,
                instalment_number=i,
                due_date=due_date,
                principal_due=p_due,
                interest_due=i_due,
                total_due=p_due + i_due,
                balance_after=balance,
            ))

        RepaymentSchedule.objects.bulk_create(schedules)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Portfolio summary stats for dashboards."""
        qs = self.get_queryset().filter(status__in=['ACTIVE', 'DISBURSED'])
        stats = qs.aggregate(
            total_portfolio=Sum('outstanding_principal'),
            total_loans=Count('id'),
            total_arrears=Sum('arrears_amount'),
        )
        par30 = qs.filter(days_past_due__gte=30).aggregate(
            par30_balance=Sum('outstanding_principal')
        )
        portfolio = stats['total_portfolio'] or 0
        par30_bal = par30['par30_balance'] or 0
        par30_pct = (par30_bal / portfolio * 100) if portfolio > 0 else 0

        return Response({
            'total_portfolio': str(portfolio),
            'total_loans': stats['total_loans'],
            'total_arrears': str(stats['total_arrears'] or 0),
            'par30_balance': str(par30_bal),
            'par30_pct': round(par30_pct, 2),
        })


# ─── REPAYMENTS ───

class RepaymentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Repayment.objects.filter(reversed=False)
    serializer_class = RepaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        loan = self.request.query_params.get('loan')
        if loan:
            qs = qs.filter(loan_id=loan)
        return qs.order_by('-received_at')

    @action(detail=False, methods=['post'])
    def capture(self, request):
        """Capture a repayment — supports offline sync."""
        serializer = RepaymentCaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        loan = Loan.objects.get(id=data['loan_id'], tenant_id=request.tenant_id)
        user = User.objects.get(auth_user_id=request.supabase_user_id)
        amount = data['amount']

        # Apply to next due schedule entry
        schedule = loan.schedule.filter(status__in=['PENDING', 'PARTIAL', 'OVERDUE']).order_by('instalment_number').first()

        # Split amount into principal and interest based on schedule
        if schedule:
            interest_remaining = schedule.interest_due - schedule.interest_paid
            interest_applied = min(amount, interest_remaining)
            principal_applied = amount - interest_applied
        else:
            # No schedule entry — apply all to principal
            interest_applied = 0
            principal_applied = amount

        # Generate receipt number
        count = Repayment.objects.filter(tenant_id=request.tenant_id).count() + 1
        receipt = f"RCP-{timezone.now().strftime('%Y%m%d')}-{count:06d}"

        repayment = Repayment.objects.create(
            tenant_id=request.tenant_id,
            loan=loan,
            schedule=schedule,
            amount=amount,
            currency=loan.currency,
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference', ''),
            received_by=user,
            received_at=data['received_at'],
            principal_applied=principal_applied,
            interest_applied=interest_applied,
            receipt_number=receipt,
            sync_id=data.get('sync_id'),
            sync_status='SYNCED',
            device_id=data.get('device_id', ''),
            client_created_at=data.get('client_created_at'),
            server_confirmed_at=timezone.now(),
        )

        # Update schedule
        if schedule:
            schedule.principal_paid += principal_applied
            schedule.interest_paid += interest_applied
            schedule.total_paid += amount
            if schedule.total_paid >= schedule.total_due:
                schedule.status = 'PAID'
                schedule.paid_date = timezone.now().date()
            else:
                schedule.status = 'PARTIAL'
            schedule.save()

        # Update loan balances
        loan.outstanding_principal = max(loan.outstanding_principal - principal_applied, 0)
        if loan.outstanding_principal == 0:
            loan.status = 'CLOSED'
            loan.closed_date = timezone.now().date()
        loan.save()

        return Response({
            'repayment': RepaymentSerializer(repayment).data,
            'receipt_number': receipt,
            'remaining_balance': str(loan.outstanding_principal),
        }, status=201)


# ─── DEPOSITS ───

class DepositProductViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    from apps.deposits.models import DepositProduct
    queryset = DepositProduct.objects.filter(is_active=True)
    serializer_class = DepositProductSerializer


class DepositAccountViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    from apps.deposits.models import DepositAccount
    queryset = DepositAccount.objects.filter(status__in=['ACTIVE', 'DORMANT'])
    serializer_class = DepositAccountSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        client = self.request.query_params.get('client')
        if client:
            qs = qs.filter(client_id=client)
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        return qs.select_related('client', 'product')

    def perform_create(self, serializer):
        from apps.deposits.models import DepositAccount
        tenant_id = self.request.tenant_id
        count = DepositAccount.objects.filter(tenant_id=tenant_id).count() + 1
        from django.utils import timezone
        account_number = f"SA-{timezone.now().strftime('%Y%m')}-{count:06d}"
        serializer.save(tenant_id=tenant_id, account_number=account_number)

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """Post a deposit transaction to an account."""
        from apps.deposits.models import DepositTransaction
        account = self.get_object()
        if account.status != 'ACTIVE':
            return Response({'error': 'Account is not active'}, status=400)

        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'amount is required'}, status=400)

        from decimal import Decimal
        amount = Decimal(str(amount))
        user = User.objects.get(auth_user_id=request.supabase_user_id)

        account.balance += amount
        account.save(update_fields=['balance'])

        txn = DepositTransaction.objects.create(
            tenant_id=request.tenant_id,
            account=account,
            transaction_type='DEPOSIT',
            amount=amount,
            balance_after=account.balance,
            description=request.data.get('description', ''),
            payment_method=request.data.get('payment_method', 'CASH'),
            reference=request.data.get('reference', ''),
            performed_by=user,
        )
        return Response(DepositTransactionSerializer(txn).data, status=201)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Post a withdrawal transaction from an account."""
        from apps.deposits.models import DepositTransaction
        from decimal import Decimal
        account = self.get_object()
        if account.status != 'ACTIVE':
            return Response({'error': 'Account is not active'}, status=400)

        amount = Decimal(str(request.data.get('amount', 0)))
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        if amount > account.balance:
            return Response({'error': 'Insufficient balance'}, status=400)

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        account.balance -= amount
        account.save(update_fields=['balance'])

        txn = DepositTransaction.objects.create(
            tenant_id=request.tenant_id,
            account=account,
            transaction_type='WITHDRAWAL',
            amount=amount,
            balance_after=account.balance,
            description=request.data.get('description', ''),
            payment_method=request.data.get('payment_method', 'CASH'),
            reference=request.data.get('reference', ''),
            performed_by=user,
        )
        return Response(DepositTransactionSerializer(txn).data, status=201)


class DepositTransactionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    from apps.deposits.models import DepositTransaction
    queryset = DepositTransaction.objects.all()
    serializer_class = DepositTransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        account = self.request.query_params.get('account')
        if account:
            qs = qs.filter(account_id=account)
        return qs.order_by('-created_at')


# ─── INVESTORS ───

class InvestorProfileViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    from apps.investors.models import InvestorProfile
    queryset = InvestorProfile.objects.filter(status='ACTIVE')
    serializer_class = InvestorProfileSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        return qs.select_related('user')

    @action(detail=True, methods=['post'])
    def create_share_link(self, request, pk=None):
        """Generate a shareable investor dashboard link."""
        import secrets
        from apps.investors.models import InvestorShareLink
        from django.utils import timezone
        from datetime import timedelta

        investor = self.get_object()
        user = User.objects.get(auth_user_id=request.supabase_user_id)

        days_valid = int(request.data.get('days_valid', 30))
        max_views = request.data.get('max_views')

        token = secrets.token_urlsafe(48)
        link = InvestorShareLink.objects.create(
            tenant_id=request.tenant_id,
            investor_profile=investor,
            token=token,
            expires_at=timezone.now() + timedelta(days=days_valid),
            max_views=max_views,
            created_by=user,
        )
        return Response({
            'token': token,
            'expires_at': link.expires_at,
            'share_url': f'/share/{token}',
        }, status=201)

    @action(detail=False, methods=['get'])
    def portfolio_summary(self, request):
        """Aggregate portfolio view for all investors."""
        from django.db.models import Sum
        qs = self.get_queryset()
        summary = qs.aggregate(
            total_invested=Sum('invested_amount_local'),
            total_current_value=Sum('current_value_local'),
        )
        return Response({
            'investor_count': qs.count(),
            'total_invested_local': str(summary['total_invested'] or 0),
            'total_current_value_local': str(summary['total_current_value'] or 0),
        })


class InvestorShareLinkViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    from apps.investors.models import InvestorShareLink
    queryset = InvestorShareLink.objects.filter(is_active=True)
    serializer_class = InvestorShareLinkSerializer


# ─── COMPLIANCE ───

class AmlAlertViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    from apps.compliance.models import AmlAlert
    queryset = AmlAlert.objects.all()
    serializer_class = AmlAlertSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        severity = self.request.query_params.get('severity')
        if severity:
            qs = qs.filter(risk_score__gte={'LOW': 0, 'MEDIUM': 40, 'HIGH': 70}.get(severity, 0))
        return qs.select_related('client', 'assigned_to').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign an AML alert to a compliance officer."""
        alert = self.get_object()
        user_id = request.data.get('user_id')
        try:
            assignee = User.objects.get(id=user_id, tenant_id=request.tenant_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        alert.assigned_to = assignee
        alert.status = 'UNDER_REVIEW'
        alert.save()
        return Response(AmlAlertSerializer(alert).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an AML alert with no further action."""
        alert = self.get_object()
        alert.status = 'CLOSED_NO_ACTION'
        alert.review_notes = request.data.get('review_notes', '')
        alert.closed_at = timezone.now()
        alert.closed_by = User.objects.get(auth_user_id=request.supabase_user_id)
        alert.save()
        return Response(AmlAlertSerializer(alert).data)


class PrudentialReturnViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    from apps.compliance.models import PrudentialReturn
    queryset = PrudentialReturn.objects.all()
    serializer_class = PrudentialReturnSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        return qs.order_by('-due_date')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Mark a prudential return as submitted."""
        pr = self.get_object()
        if pr.status not in ('GENERATED', 'REVIEWED'):
            return Response({'error': f'Cannot submit return in {pr.status} status'}, status=400)
        user = User.objects.get(auth_user_id=request.supabase_user_id)
        pr.status = 'SUBMITTED'
        pr.submitted_by = user
        pr.submitted_at = timezone.now()
        pr.submitted_values = request.data.get('submitted_values', pr.system_computed_values)
        pr.save()
        return Response(PrudentialReturnSerializer(pr).data)


# ─── MOBILE MONEY ───

class MobileMoneyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    from apps.mobile_money.models import MobileMoneyProvider
    queryset = MobileMoneyProvider.objects.filter(is_active=True)
    serializer_class = MobileMoneyProviderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country__country_code=country)
        return qs


class MobileMoneyTransactionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    from apps.mobile_money.models import MobileMoneyTransaction
    queryset = MobileMoneyTransaction.objects.all()
    serializer_class = MobileMoneyTransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        txn_type = self.request.query_params.get('type')
        if txn_type:
            qs = qs.filter(transaction_type=txn_type)
        loan = self.request.query_params.get('loan')
        if loan:
            qs = qs.filter(loan_id=loan)
        return qs.select_related('provider', 'client').order_by('-initiated_at')

    @action(detail=False, methods=['post'])
    def collect(self, request):
        """Initiate a mobile money collection for a loan repayment."""
        from apps.mobile_money.service import MobileMoneyService
        from decimal import Decimal

        serializer = CollectRepaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        try:
            txn = MobileMoneyService.collect_repayment(
                tenant_id=request.tenant_id,
                loan_id=str(data['loan_id']),
                phone_number=data['phone_number'],
                amount=data['amount'],
                provider_code=data['provider_code'],
                initiated_by_id=str(user.id),
                device_id=data.get('device_id', ''),
            )
            return Response(MobileMoneyTransactionSerializer(txn).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def disburse(self, request):
        """Initiate a mobile money loan disbursement."""
        from apps.mobile_money.service import MobileMoneyService

        serializer = DisburseLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        try:
            txn = MobileMoneyService.disburse_loan(
                tenant_id=request.tenant_id,
                loan_id=str(data['loan_id']),
                phone_number=data['phone_number'],
                amount=data['amount'],
                provider_code=data['provider_code'],
                initiated_by_id=str(user.id),
            )
            return Response(MobileMoneyTransactionSerializer(txn).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def callback(self, request, pk=None):
        """Handle mobile money provider webhook callback."""
        from apps.mobile_money.service import MobileMoneyService
        txn = self.get_object()
        result = MobileMoneyService.handle_callback(
            provider_code=txn.provider.provider_code,
            callback_data=request.data,
        )
        if result:
            return Response(MobileMoneyTransactionSerializer(result).data)
        return Response({'status': 'processed'})


# ─── REPORTS ───

class ReportDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    from apps.reports.models import ReportDefinition
    queryset = ReportDefinition.objects.filter(is_active=True)
    serializer_class = ReportDefinitionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class ReportRunViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    from apps.reports.models import ReportRun
    queryset = ReportRun.objects.all()
    serializer_class = ReportRunSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        report = self.request.query_params.get('report')
        if report:
            qs = qs.filter(report__report_code=report)
        return qs.select_related('report', 'generated_by').order_by('-created_at')

    @action(detail=False, methods=['post'])
    def request_report(self, request):
        """Queue an ad-hoc report generation."""
        from apps.reports.models import ReportDefinition, ReportRun

        serializer = RequestReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            report_def = ReportDefinition.objects.get(
                report_code=data['report_code'], is_active=True
            )
        except ReportDefinition.DoesNotExist:
            return Response({'error': f'Report {data["report_code"]} not found'}, status=404)

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        run = ReportRun.objects.create(
            tenant_id=request.tenant_id,
            report=report_def,
            parameters=data.get('parameters', {}),
            output_format=data['output_format'],
            generated_by=user,
        )

        # Trigger async generation
        from apps.tasks import generate_reports
        generate_reports.delay()

        return Response(ReportRunSerializer(run).data, status=201)


# ─── ONBOARDING / IMPORT ───

class ImportJobViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    from apps.onboarding.models import ImportJob
    queryset = ImportJob.objects.all()
    serializer_class = ImportJobSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        import_type = self.request.query_params.get('import_type')
        if import_type:
            qs = qs.filter(import_type=import_type)
        return qs.select_related('uploaded_by').order_by('-created_at')

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Upload and validate a CSV/Excel file for import."""
        from apps.onboarding.import_engine import ImportValidationEngine
        from apps.onboarding.models import ImportJob

        import_type = request.data.get('import_type', '').upper()
        if import_type not in ['CLIENTS', 'LOANS', 'CHART_OF_ACCOUNTS', 'OPENING_BALANCES']:
            return Response({'error': f'Unsupported import type: {import_type}'}, status=400)

        if 'file' not in request.FILES:
            return Response({'error': 'file is required'}, status=400)

        uploaded_file = request.FILES['file']
        user = User.objects.get(auth_user_id=request.supabase_user_id)

        job = ImportJob.objects.create(
            tenant_id=request.tenant_id,
            import_type=import_type,
            file_path=f'imports/{request.tenant_id}/{uploaded_file.name}',
            file_name=uploaded_file.name,
            file_size_bytes=uploaded_file.size,
            status='VALIDATING',
            uploaded_by=user,
        )

        try:
            engine = ImportValidationEngine(
                tenant_id=request.tenant_id,
                import_type=import_type,
            )
            result = engine.validate_csv(uploaded_file.read())

            job.status = 'VALIDATION_COMPLETE'
            job.total_rows = result['total_rows']
            job.valid_rows = result['valid_rows']
            job.error_rows = result['error_rows']
            job.warning_rows = result['warning_rows']
            job.validation_errors = result['errors']
            job.validation_warnings = result['warnings']
            job.save()

            return Response({
                'job_id': str(job.id),
                'status': job.status,
                **result,
            })
        except Exception as e:
            job.status = 'FAILED'
            job.error_message = str(e)[:500]
            job.save()
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        """Commit a validated import — create records from the uploaded file."""
        from apps.onboarding.import_engine import commit_import
        job = self.get_object()

        if job.status != 'VALIDATION_COMPLETE':
            return Response(
                {'error': f'Cannot commit import in {job.status} status. Must be VALIDATION_COMPLETE.'},
                status=400
            )

        user = User.objects.get(auth_user_id=request.supabase_user_id)
        job.approved_by = user
        job.approved_at = timezone.now()
        job.save(update_fields=['approved_by', 'approved_at'])

        try:
            result = commit_import(str(job.id))
            return Response({
                'job_id': str(job.id),
                'status': 'COMPLETED',
                'imported': result['imported'],
                'skipped': result['skipped'],
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
