from django.db import models
from apps.core_models import BaseModel, TenantModel, SyncModel


class MobileMoneyProvider(BaseModel):
    """Provider-agnostic mobile money configuration per country."""
    country = models.ForeignKey('tenants.CountryPack', on_delete=models.CASCADE, related_name='momo_providers')
    provider_code = models.CharField(max_length=30)
    provider_name = models.CharField(max_length=100)
    API_TYPE_CHOICES = [
        ('AFRICAS_TALKING', "Africa's Talking"), ('DIRECT_API', 'Direct API'), ('MANUAL', 'Manual'),
    ]
    api_type = models.CharField(max_length=30, choices=API_TYPE_CHOICES)
    api_config = models.JSONField(default=dict, help_text='Encrypted API credentials and endpoints')
    currency = models.CharField(max_length=3)
    phone_prefix = models.CharField(max_length=10, blank=True)
    phone_regex = models.CharField(max_length=100, blank=True, help_text='Validation regex for phone numbers')
    min_transaction = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    max_transaction = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    fee_structure = models.JSONField(default=dict, blank=True)
    settlement_gl_account = models.ForeignKey(
        'ledger.GlAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'mobile_money_providers'
        unique_together = [('country', 'provider_code')]

    def __str__(self):
        return f"{self.provider_name} ({self.country.country_code})"


class MobileMoneyTransaction(TenantModel, SyncModel):
    """Mobile money transaction record — collections, disbursements, deposits, withdrawals."""
    provider = models.ForeignKey(MobileMoneyProvider, on_delete=models.PROTECT, related_name='transactions')
    TXN_TYPE_CHOICES = [
        ('COLLECTION', 'Collection'), ('DISBURSEMENT', 'Disbursement'),
        ('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal'), ('REVERSAL', 'Reversal'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TXN_TYPE_CHOICES)
    DIRECTION_CHOICES = [('IN', 'Inbound'), ('OUT', 'Outbound')]
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES)
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3)
    fee_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    FEE_BEARER_CHOICES = [('CLIENT', 'Client'), ('MFI', 'MFI')]
    fee_bearer = models.CharField(max_length=10, choices=FEE_BEARER_CHOICES, default='CLIENT')
    # Business record links
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='momo_transactions')
    loan = models.ForeignKey('loans.Loan', on_delete=models.SET_NULL, null=True, blank=True, related_name='momo_transactions')
    deposit_account = models.ForeignKey('deposits.DepositAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='momo_transactions')
    repayment = models.ForeignKey('loans.Repayment', on_delete=models.SET_NULL, null=True, blank=True, related_name='momo_transactions')
    # Provider references
    provider_reference = models.CharField(max_length=100, blank=True)
    internal_reference = models.CharField(max_length=100)
    # Status
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'), ('PENDING', 'Pending'), ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'), ('REVERSED', 'Reversed'), ('TIMEOUT', 'Timeout'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    status_message = models.TextField(blank=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # Reconciliation
    reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    gl_transaction = models.ForeignKey(
        'ledger.GlTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    initiated_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='+')

    class Meta:
        db_table = 'mobile_money_transactions'
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_momo_status'),
        ]


class MobileMoneyReconciliation(TenantModel):
    """Daily reconciliation between provider statements and system records."""
    provider = models.ForeignKey(MobileMoneyProvider, on_delete=models.PROTECT, related_name='reconciliations')
    reconciliation_date = models.DateField()
    statement_file_path = models.TextField(blank=True)
    statement_total = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    statement_count = models.IntegerField(null=True, blank=True)
    system_total = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    system_count = models.IntegerField(null=True, blank=True)
    matched_count = models.IntegerField(default=0)
    unmatched_system = models.IntegerField(default=0)
    unmatched_provider = models.IntegerField(default=0)
    variance_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'), ('EXCEPTION', 'Exception'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    completed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'mobile_money_reconciliation'
