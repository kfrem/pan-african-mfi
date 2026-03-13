import uuid
from django.db import models
from apps.core_models import BaseModel, TenantModel, SoftDeleteModel


class User(TenantModel, SoftDeleteModel):
    """Platform user — extends Supabase auth.users with tenant/role/profile data."""
    auth_user_id = models.UUIDField(unique=True, help_text='FK to Supabase auth.users')
    email = models.EmailField(max_length=255)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    failed_login_count = models.IntegerField(default=0)
    last_login_at = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    language_preference = models.CharField(max_length=5, default='en')
    theme_preference = models.CharField(max_length=30, default='professional_light')

    class Meta:
        db_table = 'users'
        unique_together = [('tenant', 'email')]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Role(TenantModel):
    """Predefined and custom roles per tenant."""
    role_code = models.CharField(max_length=50)
    role_name = models.CharField(max_length=100)
    is_system_role = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'roles'
        unique_together = [('tenant', 'role_code')]

    def __str__(self):
        return f"{self.role_name} ({self.tenant})"


class Permission(BaseModel):
    """Global permissions — not tenant-scoped."""
    permission_code = models.CharField(max_length=100, unique=True)
    resource = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permissions'

    def __str__(self):
        return self.permission_code


class RolePermission(models.Model):
    """Many-to-many: which permissions each role has."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')

    class Meta:
        db_table = 'role_permissions'
        unique_together = [('role', 'permission')]


class UserRole(models.Model):
    """Many-to-many: users can hold multiple roles simultaneously."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        db_table = 'user_roles'
        unique_together = [('user', 'role')]


class MakerCheckerConfig(TenantModel):
    """Configurable approval workflows per tenant."""
    action_type = models.CharField(max_length=100)
    min_approvals = models.IntegerField(default=1)
    required_roles = models.JSONField(default=list)
    amount_threshold = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    amount_currency = models.CharField(max_length=3, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'maker_checker_configs'
        unique_together = [('tenant', 'action_type', 'amount_threshold')]

    def __str__(self):
        return f"{self.action_type} ({self.tenant})"


class ApprovalRequest(TenantModel):
    """Maker-checker workflow instance."""
    action_type = models.CharField(max_length=100)
    target_table = models.CharField(max_length=100)
    target_id = models.UUIDField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_requests')
    payload = models.JSONField()
    STATUS_CHOICES = [('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'approval_requests'

    def __str__(self):
        return f"{self.action_type} - {self.status}"


class ApprovalDecision(BaseModel):
    """Individual checker decision on an approval request."""
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='decisions')
    decided_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_decisions')
    DECISION_CHOICES = [('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'approval_decisions'


class ActiveSession(TenantModel):
    """Tracked user sessions for security monitoring."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token_hash = models.CharField(max_length=255)
    DEVICE_CHOICES = [('DESKTOP', 'Desktop'), ('TABLET', 'Tablet'), ('MOBILE', 'Mobile')]
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, blank=True)
    device_info = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    location_country = models.CharField(max_length=2, blank=True)
    location_city = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    terminated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    TERMINATION_CHOICES = [
        ('LOGOUT', 'Logout'), ('TIMEOUT', 'Timeout'),
        ('ADMIN_KILL', 'Admin Kill'), ('SUSPICIOUS', 'Suspicious'),
    ]
    terminated_reason = models.CharField(max_length=50, choices=TERMINATION_CHOICES, blank=True)

    class Meta:
        db_table = 'active_sessions'
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_active'], name='idx_sessions_active',
                         condition=models.Q(is_active=True)),
        ]


class SessionConfig(TenantModel):
    """Per-role session timeout and security settings."""
    role_code = models.CharField(max_length=50, blank=True,
                                 help_text='Blank = applies to all roles')
    session_timeout_minutes = models.IntegerField(default=480)
    max_concurrent_sessions = models.IntegerField(default=3)
    require_ip_whitelist = models.BooleanField(default=False)
    require_mfa = models.BooleanField(default=False)

    class Meta:
        db_table = 'session_configs'
        unique_together = [('tenant', 'role_code')]


class IpWhitelist(TenantModel):
    """Optional IP restrictions per tenant."""
    ip_range = models.CharField(max_length=50, help_text='CIDR notation e.g. 192.168.1.0/24')
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')

    class Meta:
        db_table = 'ip_whitelists'
