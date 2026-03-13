from django.db import models


class AuditLog(models.Model):
    """Immutable audit trail — INSERT and SELECT only, no UPDATE/DELETE."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(null=True, blank=True)
    user_email = models.CharField(max_length=255, blank=True)
    user_role = models.CharField(max_length=50, blank=True)
    ACTION_CHOICES = [
        ('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'),
        ('LOGIN', 'Login'), ('LOGOUT', 'Logout'), ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'), ('EXPORT', 'Export'), ('VIEW_SENSITIVE', 'View Sensitive'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    changed_fields = models.JSONField(null=True, blank=True)
    justification = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit"."logs'  # Separate schema in PostgreSQL
        managed = False  # Created via raw SQL migration
        indexes = [
            models.Index(fields=['tenant_id', 'created_at'], name='idx_audit_tenant_date'),
            models.Index(fields=['tenant_id', 'resource_type', 'resource_id'], name='idx_audit_resource'),
        ]


class LoginAttempt(models.Model):
    """Login attempt log — append-only."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(null=True, blank=True)
    email = models.CharField(max_length=255)
    success = models.BooleanField()
    failure_reason = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit"."login_attempts'
        managed = False
