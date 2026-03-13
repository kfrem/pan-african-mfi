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
            total_interest = principal * (rate / 100) * (term / 12)
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
                loan=loan,
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
