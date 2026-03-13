from django.db import models
from apps.core_models import BaseModel, TenantModel


class ReportDefinition(BaseModel):
    """System and custom report definitions."""
    report_code = models.CharField(max_length=50, unique=True)
    report_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    CATEGORY_CHOICES = [
        ('FINANCIAL', 'Financial'), ('PORTFOLIO', 'Portfolio'), ('REGULATORY', 'Regulatory'),
        ('COMPLIANCE', 'Compliance'), ('OPERATIONAL', 'Operational'),
        ('INVESTOR', 'Investor'), ('BOARD', 'Board'),
    ]
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    applicable_roles = models.JSONField(default=list)
    parameters = models.JSONField(default=list, help_text='Parameter definitions')
    output_formats = models.JSONField(default=list)
    template_path = models.TextField(blank=True)
    query_config = models.JSONField(null=True, blank=True)
    is_system = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'report_definitions'

    def __str__(self):
        return f"{self.report_name} ({self.report_code})"


class ReportSchedule(TenantModel):
    """Automated report generation schedule."""
    report = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE, related_name='schedules')
    schedule_name = models.CharField(max_length=255)
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'), ('ANNUAL', 'Annual'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    day_of_week = models.IntegerField(null=True, blank=True, help_text='1=Monday for WEEKLY')
    day_of_month = models.IntegerField(null=True, blank=True, help_text='1-28 for MONTHLY')
    time_of_day = models.TimeField(default='06:00:00')
    parameters = models.JSONField(default=dict, blank=True)
    output_format = models.CharField(max_length=10, default='PDF')
    recipients = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    next_run_at = models.DateTimeField()
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')

    class Meta:
        db_table = 'report_schedules'

    def __str__(self):
        return f"{self.schedule_name} ({self.frequency})"


class ReportRun(TenantModel):
    """Individual report generation instance — scheduled or ad-hoc."""
    report = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE, related_name='runs')
    schedule = models.ForeignKey(ReportSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs')
    parameters = models.JSONField(default=dict)
    output_format = models.CharField(max_length=10)
    STATUS_CHOICES = [
        ('QUEUED', 'Queued'), ('GENERATING', 'Generating'),
        ('COMPLETED', 'Completed'), ('FAILED', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    file_path = models.TextField(blank=True, help_text='Supabase Storage path')
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    generation_time_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'report_runs'
        indexes = [
            models.Index(fields=['tenant', '-created_at'], name='idx_report_runs_recent'),
        ]
