from django.db import models
from apps.core_models import TenantModel, BaseModel, SyncModel


class GlAccount(TenantModel):
    """Chart of accounts — fully configurable per tenant."""
    account_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'Asset'), ('LIABILITY', 'Liability'), ('EQUITY', 'Equity'),
        ('INCOME', 'Income'), ('EXPENSE', 'Expense'),
    ]
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_header = models.BooleanField(default=False, help_text='Summary account — no direct postings')
    is_system_account = models.BooleanField(default=False, help_text='Auto-created, cannot be deleted')
    BALANCE_CHOICES = [('D', 'Debit'), ('C', 'Credit')]
    normal_balance = models.CharField(max_length=1, choices=BALANCE_CHOICES)
    currency = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    regulatory_mapping_code = models.CharField(max_length=50, blank=True,
                                               help_text='Maps to prudential return line item')

    class Meta:
        db_table = 'gl_accounts'
        unique_together = [('tenant', 'account_code')]

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"


class AccountingPeriod(TenantModel):
    """Accounting periods with open/close control."""
    period_name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    STATUS_CHOICES = [('OPEN', 'Open'), ('CLOSING', 'Closing'), ('CLOSED', 'Closed')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    closed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounting_periods'
        unique_together = [('tenant', 'period_name')]

    def __str__(self):
        return f"{self.period_name} ({self.status})"


class GlTransaction(TenantModel, SyncModel):
    """Double-entry transaction header — groups related GL entries."""
    transaction_ref = models.CharField(max_length=50)
    transaction_date = models.DateField()
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT, related_name='transactions')
    description = models.TextField(blank=True)
    SOURCE_TYPE_CHOICES = [
        ('LOAN_DISBURSEMENT', 'Loan Disbursement'), ('REPAYMENT', 'Repayment'),
        ('DEPOSIT', 'Deposit'), ('MANUAL', 'Manual'), ('FEE', 'Fee'),
        ('PROVISION', 'Provision'), ('INTEREST_ACCRUAL', 'Interest Accrual'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES, blank=True)
    source_id = models.UUIDField(null=True, blank=True)
    posted_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='+')
    is_reversal = models.BooleanField(default=False)
    reverses_transaction = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'gl_transactions'

    def __str__(self):
        return f"{self.transaction_ref} ({self.transaction_date})"


class GlEntry(TenantModel):
    """Individual debit/credit line within a GL transaction."""
    transaction = models.ForeignKey(GlTransaction, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(GlAccount, on_delete=models.PROTECT, related_name='entries')
    debit_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    credit_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    currency = models.CharField(max_length=3)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'gl_entries'
        indexes = [
            models.Index(fields=['tenant', 'account'], name='idx_gl_entries_account'),
        ]


class ExchangeRate(BaseModel):
    """Daily exchange rates — not tenant-scoped (global reference data)."""
    base_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=19, decimal_places=8)
    rate_date = models.DateField()
    source = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'exchange_rates'
        unique_together = [('base_currency', 'target_currency', 'rate_date')]

    def __str__(self):
        return f"{self.base_currency}/{self.target_currency} = {self.rate} ({self.rate_date})"
