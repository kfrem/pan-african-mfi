"""
REST API Serializers — Pan-African Microfinance SaaS
Covers: Tenant setup, User auth, Client CRUD, Loan lifecycle
"""
from rest_framework import serializers
from apps.tenants.models import Tenant, CountryPack, LicenceTier, Branch, LicenceProfile
from apps.accounts.models import User, Role, UserRole
from apps.clients.models import Client, Group, GroupMember, KycDocument
from apps.loans.models import LoanProduct, Loan, RepaymentSchedule, Repayment


# ─── TENANT & CONFIG ───

class CountryPackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryPack
        fields = ['country_code', 'country_name', 'regulatory_authority',
                  'default_currency', 'default_language', 'config']
        read_only_fields = ['country_code']


class LicenceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicenceTier
        fields = ['id', 'country', 'tier_code', 'tier_name',
                  'can_accept_deposits', 'can_offer_savings', 'can_do_transfers',
                  'credit_only', 'min_capital_amount', 'car_requirement_pct',
                  'single_obligor_limit_pct', 'reporting_frequency']


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'branch_code', 'branch_name', 'branch_type', 'address', 'is_active']
        read_only_fields = ['id']


class TenantSerializer(serializers.ModelSerializer):
    licence_tier_name = serializers.CharField(source='licence_tier.tier_name', read_only=True)
    country_name = serializers.CharField(source='country.country_name', read_only=True)

    class Meta:
        model = Tenant
        fields = ['id', 'name', 'trading_name', 'country', 'country_name',
                  'licence_tier', 'licence_tier_name', 'status', 'default_currency',
                  'default_language', 'timezone', 'logo_url',
                  'primary_brand_colour', 'secondary_brand_colour',
                  'custom_domain', 'tagline']
        read_only_fields = ['id', 'status']


class TenantOnboardingSerializer(serializers.Serializer):
    """Used during initial tenant setup — creates tenant + admin user + licence profile."""
    institution_name = serializers.CharField(max_length=255)
    trading_name = serializers.CharField(max_length=255, required=False, default='')
    country_code = serializers.CharField(max_length=2)
    licence_tier_id = serializers.UUIDField()
    admin_email = serializers.EmailField()
    admin_full_name = serializers.CharField(max_length=255)
    admin_phone = serializers.CharField(max_length=20, required=False, default='')


# ─── AUTH & USERS ───

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True, default='')

    class Meta:
        model = User
        fields = ['id', 'auth_user_id', 'email', 'full_name', 'phone',
                  'branch', 'branch_name', 'is_active', 'is_locked',
                  'mfa_enabled', 'language_preference', 'theme_preference',
                  'last_login_at', 'roles']
        read_only_fields = ['id', 'auth_user_id', 'is_locked', 'last_login_at']

    def get_roles(self, obj):
        return list(obj.user_roles.values_list('role__role_code', flat=True))


class UserCreateSerializer(serializers.ModelSerializer):
    role_codes = serializers.ListField(child=serializers.CharField(), write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'branch', 'role_codes']

    def create(self, validated_data):
        role_codes = validated_data.pop('role_codes', [])
        tenant = self.context['request'].tenant
        # Supabase auth user creation happens via Supabase Admin API
        # Here we create the platform user record
        user = User.objects.create(tenant=tenant, **validated_data)
        roles = Role.objects.filter(tenant=tenant, role_code__in=role_codes)
        for role in roles:
            UserRole.objects.create(user=user, role=role)
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'role_code', 'role_name', 'is_system_role', 'description']
        read_only_fields = ['id', 'is_system_role']


# ─── CLIENTS ───

class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits heavy fields."""
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    officer_name = serializers.CharField(source='assigned_officer.full_name', read_only=True, default='')

    class Meta:
        model = Client
        fields = ['id', 'client_number', 'full_legal_name', 'client_type',
                  'phone_primary', 'kyc_status', 'risk_rating',
                  'branch', 'branch_name', 'assigned_officer', 'officer_name',
                  'is_insider', 'is_pep', 'created_at']


class ClientDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/create/update views."""
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)
    officer_name = serializers.CharField(source='assigned_officer.full_name', read_only=True, default='')
    active_loans_count = serializers.SerializerMethodField()
    total_exposure = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'client_number', 'kyc_verified_by',
                           'kyc_verified_at', 'sync_id', 'sync_status',
                           'server_confirmed_at', 'created_at', 'updated_at']

    def get_active_loans_count(self, obj):
        return obj.loans.filter(status__in=['ACTIVE', 'DISBURSED']).count()

    def get_total_exposure(self, obj):
        from django.db.models import Sum
        result = obj.loans.filter(
            status__in=['ACTIVE', 'DISBURSED']
        ).aggregate(total=Sum('outstanding_principal'))
        return str(result['total'] or 0)


class GroupSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    leader_name = serializers.CharField(source='leader.full_legal_name', read_only=True, default='')

    class Meta:
        model = Group
        fields = ['id', 'group_number', 'group_name', 'branch',
                  'leader', 'leader_name', 'meeting_frequency', 'meeting_day',
                  'is_active', 'member_count', 'created_at']
        read_only_fields = ['id', 'group_number']

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class KycDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)

    class Meta:
        model = KycDocument
        fields = ['id', 'client', 'document_type', 'file_path', 'file_name',
                  'file_size_bytes', 'uploaded_by', 'uploaded_by_name',
                  'verified', 'verified_by', 'verified_at', 'expiry_date', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'verified_by', 'verified_at']


# ─── LOANS ───

class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = ['id', 'product_code', 'product_name', 'product_type',
                  'min_amount', 'max_amount', 'min_term_months', 'max_term_months',
                  'interest_method', 'default_interest_rate_pct',
                  'origination_fee_pct', 'insurance_fee_pct',
                  'requires_collateral', 'requires_guarantor',
                  'group_liability_type', 'allowed_frequencies', 'is_active']
        read_only_fields = ['id']


class LoanListSerializer(serializers.ModelSerializer):
    """Lightweight for list views."""
    client_name = serializers.CharField(source='client.full_legal_name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    officer_name = serializers.CharField(source='loan_officer.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.branch_name', read_only=True)

    class Meta:
        model = Loan
        fields = ['id', 'loan_number', 'client', 'client_name',
                  'product', 'product_name', 'principal_amount', 'currency',
                  'outstanding_principal', 'status', 'classification',
                  'days_past_due', 'disbursement_date', 'maturity_date',
                  'loan_officer', 'officer_name', 'branch_name',
                  'is_insider_loan', 'override_flag']


class LoanDetailSerializer(serializers.ModelSerializer):
    """Full detail for loan view/create."""
    client_name = serializers.CharField(source='client.full_legal_name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    schedule = serializers.SerializerMethodField()
    repayments_count = serializers.SerializerMethodField()
    total_repaid = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'loan_number', 'outstanding_principal',
                           'outstanding_interest', 'arrears_amount', 'days_past_due',
                           'classification', 'provision_rate_pct', 'provision_amount',
                           'approved_by', 'disbursed_by', 'closed_date',
                           'sync_id', 'sync_status', 'created_at', 'updated_at']

    def get_schedule(self, obj):
        return RepaymentScheduleSerializer(
            obj.schedule.order_by('instalment_number'), many=True
        ).data

    def get_repayments_count(self, obj):
        return obj.repayments.filter(reversed=False).count()

    def get_total_repaid(self, obj):
        from django.db.models import Sum
        result = obj.repayments.filter(reversed=False).aggregate(total=Sum('amount'))
        return str(result['total'] or 0)


class LoanApplicationSerializer(serializers.Serializer):
    """Simplified serializer for loan application submission."""
    client_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    branch_id = serializers.UUIDField()
    principal_amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    term_months = serializers.IntegerField(min_value=1)
    repayment_frequency = serializers.ChoiceField(choices=['DAILY', 'WEEKLY', 'FORTNIGHTLY', 'MONTHLY'])
    interest_rate_pct = serializers.DecimalField(max_digits=7, decimal_places=4, required=False)
    purpose = serializers.CharField(max_length=500, required=False, default='')
    collateral_description = serializers.CharField(required=False, default='')
    collateral_value = serializers.DecimalField(max_digits=19, decimal_places=4, required=False)
    guarantor_client_id = serializers.UUIDField(required=False)


class RepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepaymentSchedule
        fields = ['id', 'instalment_number', 'due_date',
                  'principal_due', 'interest_due', 'fees_due', 'total_due',
                  'principal_paid', 'interest_paid', 'total_paid',
                  'balance_after', 'status', 'paid_date', 'days_late']


class RepaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source='received_by.full_name', read_only=True)

    class Meta:
        model = Repayment
        fields = ['id', 'loan', 'schedule', 'amount', 'currency',
                  'payment_method', 'payment_reference', 'received_by',
                  'received_by_name', 'received_at',
                  'principal_applied', 'interest_applied', 'fees_applied',
                  'penalty_applied', 'receipt_number', 'reversed', 'created_at']
        read_only_fields = ['id', 'received_by', 'principal_applied', 'interest_applied',
                           'fees_applied', 'penalty_applied', 'receipt_number',
                           'reversed', 'created_at']


class RepaymentCaptureSerializer(serializers.Serializer):
    """Simplified serializer for capturing a repayment in the field."""
    loan_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    payment_method = serializers.ChoiceField(choices=['CASH', 'MOBILE_MONEY', 'BANK_TRANSFER', 'CHEQUE'])
    payment_reference = serializers.CharField(max_length=100, required=False, default='')
    received_at = serializers.DateTimeField()
    # Offline sync fields
    sync_id = serializers.UUIDField(required=False)
    device_id = serializers.CharField(max_length=100, required=False, default='')
    client_created_at = serializers.DateTimeField(required=False)
