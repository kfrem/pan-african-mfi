from django.db import models
from apps.core_models import BaseModel, TenantModel


class ApiKey(TenantModel):
    """Tenant-scoped API keys for third-party integrations."""
    key_prefix = models.CharField(max_length=8)
    key_hash = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=list)
    rate_limit_per_minute = models.IntegerField(default=60)
    allowed_ips = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')

    class Meta:
        db_table = 'api_keys'

    def __str__(self):
        return f"{self.key_prefix}... ({self.name})"


class Webhook(TenantModel):
    """Webhook subscriptions for event-driven integrations."""
    event_type = models.CharField(max_length=50)
    target_url = models.TextField()
    secret_hash = models.CharField(max_length=255)
    headers = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    retry_count = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=60)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    disabled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')

    class Meta:
        db_table = 'webhooks'

    def __str__(self):
        return f"{self.event_type} → {self.target_url[:50]}"


class WebhookDelivery(BaseModel):
    """Webhook delivery attempts — for debugging and reliability."""
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    attempt_number = models.IntegerField(default=1)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'), ('RETRYING', 'Retrying'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        db_table = 'webhook_deliveries'


class SyncQueue(TenantModel):
    """Offline sync queue — tracks pending uploads from devices."""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    device_id = models.CharField(max_length=100)
    target_table = models.CharField(max_length=100)
    target_sync_id = models.UUIDField()
    OPERATION_CHOICES = [('INSERT', 'Insert'), ('UPDATE', 'Update')]
    operation = models.CharField(max_length=10, choices=OPERATION_CHOICES)
    payload = models.JSONField()
    client_timestamp = models.DateTimeField()
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'), ('PROCESSING', 'Processing'),
        ('APPLIED', 'Applied'), ('CONFLICT', 'Conflict'), ('REJECTED', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sync_queue'
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_sync_pending',
                         condition=models.Q(status='QUEUED')),
        ]
