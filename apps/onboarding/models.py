from django.db import models
from apps.core_models import TenantModel


class OnboardingProgress(TenantModel):
    """Guided setup wizard progress per tenant — tracks completion of each step."""
    steps = models.JSONField(default=list, help_text='Array of step objects with status')
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    skipped_steps = models.JSONField(default=list)
    load_demo_data = models.BooleanField(default=False)

    class Meta:
        db_table = 'onboarding_progress'

    def __str__(self):
        return f"Onboarding: {self.tenant} ({'Complete' if self.is_complete else 'In Progress'})"


class ImportJob(TenantModel):
    """Bulk data import from CSV/Excel with validation and preview."""
    IMPORT_TYPE_CHOICES = [
        ('CLIENTS', 'Clients'), ('LOANS', 'Loans'), ('REPAYMENT_HISTORY', 'Repayment History'),
        ('CHART_OF_ACCOUNTS', 'Chart of Accounts'), ('OPENING_BALANCES', 'Opening Balances'),
        ('DEPOSIT_ACCOUNTS', 'Deposit Accounts'), ('GROUPS', 'Groups'),
    ]
    import_type = models.CharField(max_length=30, choices=IMPORT_TYPE_CHOICES)
    file_path = models.TextField(help_text='Supabase Storage path')
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'), ('VALIDATING', 'Validating'),
        ('VALIDATION_COMPLETE', 'Validation Complete'), ('PREVIEWING', 'Previewing'),
        ('IMPORTING', 'Importing'), ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADED')
    total_rows = models.IntegerField(null=True, blank=True)
    valid_rows = models.IntegerField(null=True, blank=True)
    error_rows = models.IntegerField(null=True, blank=True)
    warning_rows = models.IntegerField(null=True, blank=True)
    validation_errors = models.JSONField(default=list)
    validation_warnings = models.JSONField(default=list)
    imported_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'import_jobs'
