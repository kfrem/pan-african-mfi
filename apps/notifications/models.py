from django.db import models
from apps.core_models import BaseModel, TenantModel


class NotificationRule(TenantModel):
    """Configurable threshold-based alerts per tenant."""
    rule_code = models.CharField(max_length=50)
    rule_name = models.CharField(max_length=255)
    metric = models.CharField(max_length=50)
    OPERATOR_CHOICES = [('GT', '>'), ('LT', '<'), ('GTE', '>='), ('LTE', '<='), ('EQ', '=')]
    operator = models.CharField(max_length=5, choices=OPERATOR_CHOICES)
    threshold_value = models.DecimalField(max_digits=19, decimal_places=4)
    SEVERITY_CHOICES = [('INFO', 'Info'), ('WARNING', 'Warning'), ('CRITICAL', 'Critical')]
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    notify_roles = models.JSONField(default=list)
    notify_email = models.BooleanField(default=False)
    notify_sms = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'notification_rules'

    def __str__(self):
        return f"{self.rule_name} ({self.metric} {self.operator} {self.threshold_value})"


class Notification(TenantModel):
    """In-app notification delivered to a specific user."""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    rule = models.ForeignKey(NotificationRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    severity = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed = models.BooleanField(default=False)
    dismissed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_read'], name='idx_notif_unread',
                         condition=models.Q(is_read=False)),
        ]


class SmsTemplate(BaseModel):
    """SMS message templates — per country with tenant overrides."""
    country = models.ForeignKey('tenants.CountryPack', on_delete=models.CASCADE, related_name='sms_templates')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='sms_templates')
    template_code = models.CharField(max_length=50)
    language = models.CharField(max_length=5, default='en')
    message_body = models.TextField(help_text='Use {{placeholders}} for dynamic content')
    max_sms_parts = models.IntegerField(default=1, help_text='Cost control: 1 part = 160 chars')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'sms_templates'

    def __str__(self):
        return f"{self.template_code} ({self.language})"


class SmsLog(TenantModel):
    """SMS delivery log with cost tracking."""
    template = models.ForeignKey(SmsTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    recipient_phone = models.CharField(max_length=20)
    recipient_client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    recipient_user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    message_body = models.TextField()
    sms_parts = models.IntegerField(default=1)
    provider = models.CharField(max_length=30)
    provider_message_id = models.CharField(max_length=100, blank=True)
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'), ('SENT', 'Sent'), ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'), ('REJECTED', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    status_message = models.TextField(blank=True)
    cost_amount = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    cost_currency = models.CharField(max_length=3, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    TRIGGER_CHOICES = [
        ('SCHEDULER', 'Scheduler'), ('MANUAL', 'Manual'),
        ('SYSTEM_EVENT', 'System Event'), ('USSD', 'USSD'),
    ]
    triggered_by = models.CharField(max_length=30, choices=TRIGGER_CHOICES, blank=True)

    class Meta:
        db_table = 'sms_log'


class UssdSession(TenantModel):
    """USSD session tracking for borrower self-service."""
    session_id = models.CharField(max_length=100, help_text="Africa's Talking session ID")
    phone_number = models.CharField(max_length=20)
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    service_code = models.CharField(max_length=20)
    current_level = models.IntegerField(default=0)
    session_data = models.JSONField(default=dict, blank=True)
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'), ('COMPLETED', 'Completed'),
        ('TIMEOUT', 'Timeout'), ('ERROR', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_input = models.TextField(blank=True)

    class Meta:
        db_table = 'ussd_sessions'
