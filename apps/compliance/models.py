from django.db import models
from apps.core_models import TenantModel, BaseModel


class AmlAlert(TenantModel):
    """System-generated AML transaction monitoring alerts."""
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='aml_alerts')
    alert_type = models.CharField(max_length=50)
    trigger_description = models.TextField()
    trigger_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    trigger_currency = models.CharField(max_length=3, blank=True)
    source_transaction_id = models.UUIDField(null=True, blank=True)
    STATUS_CHOICES = [
        ('OPEN', 'Open'), ('UNDER_REVIEW', 'Under Review'), ('ESCALATED', 'Escalated'),
        ('STR_FILED', 'STR Filed'), ('CLOSED_NO_ACTION', 'Closed No Action'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    risk_score = models.IntegerField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'aml_alerts'


class Str(TenantModel):
    """Suspicious Transaction Reports / Cash Transaction Reports."""
    alert = models.ForeignKey(AmlAlert, on_delete=models.SET_NULL, null=True, blank=True, related_name='strs')
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='strs')
    REPORT_TYPE_CHOICES = [('STR', 'STR'), ('CTR', 'CTR')]
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    narrative = models.TextField()
    transaction_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    transaction_currency = models.CharField(max_length=3, blank=True)
    transaction_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'),
        ('ACKNOWLEDGED', 'Acknowledged'), ('REJECTED_BY_FIC', 'Rejected by FIC'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    submitted_to = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    fic_reference = models.CharField(max_length=100, blank=True)
    filed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    deadline = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'strs'
        verbose_name = 'Suspicious Transaction Report'
        verbose_name_plural = 'Suspicious Transaction Reports'


class TransactionMonitoringRule(BaseModel):
    """AML monitoring rules — configured per country pack."""
    country = models.ForeignKey('tenants.CountryPack', on_delete=models.CASCADE, related_name='monitoring_rules')
    rule_code = models.CharField(max_length=50)
    rule_name = models.CharField(max_length=255)
    RULE_TYPE_CHOICES = [('THRESHOLD', 'Threshold'), ('PATTERN', 'Pattern'), ('VELOCITY', 'Velocity')]
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    config = models.JSONField()
    SEVERITY_CHOICES = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')]
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'transaction_monitoring_rules'


class PrudentialReturn(TenantModel):
    """Regulatory returns — generated, reviewed, submitted."""
    return_template_code = models.CharField(max_length=50)
    return_name = models.CharField(max_length=255)
    reporting_period = models.CharField(max_length=20)
    due_date = models.DateField()
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), ('GENERATED', 'Generated'), ('REVIEWED', 'Reviewed'),
        ('SUBMITTED', 'Submitted'), ('OVERDUE', 'Overdue'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    data = models.JSONField(null=True, blank=True)
    system_computed_values = models.JSONField(null=True, blank=True)
    submitted_values = models.JSONField(null=True, blank=True)
    variance_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    generated_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'prudential_returns'
