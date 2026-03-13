from django.db import models
from apps.core_models import TenantModel, SyncModel


class DepositProduct(TenantModel):
    """Deposit product definitions — only for deposit-taking tenants."""
    product_code = models.CharField(max_length=20)
    product_name = models.CharField(max_length=255)
    PRODUCT_TYPE_CHOICES = [
        ('SAVINGS', 'Savings'), ('FIXED_DEPOSIT', 'Fixed Deposit'), ('CURRENT', 'Current'),
    ]
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    interest_rate_pct = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    min_balance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    notice_period_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'deposit_products'
        unique_together = [('tenant', 'product_code')]

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"


class DepositAccount(TenantModel):
    """Client deposit/savings account."""
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='deposit_accounts')
    product = models.ForeignKey(DepositProduct, on_delete=models.PROTECT, related_name='accounts')
    account_number = models.CharField(max_length=50)
    currency = models.CharField(max_length=3)
    balance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('DORMANT', 'Dormant'), ('CLOSED', 'Closed')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    opened_at = models.DateField()
    closed_at = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'deposit_accounts'
        unique_together = [('tenant', 'account_number')]

    def __str__(self):
        return f"{self.account_number} - {self.client}"


class DepositTransaction(TenantModel, SyncModel):
    """Deposit account transactions — offline-capable."""
    account = models.ForeignKey(DepositAccount, on_delete=models.PROTECT, related_name='transactions')
    TXN_TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal'),
        ('INTEREST_CREDIT', 'Interest Credit'), ('FEE_DEBIT', 'Fee Debit'), ('TRANSFER', 'Transfer'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TXN_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    balance_after = models.DecimalField(max_digits=19, decimal_places=4)
    description = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    performed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='+')
    gl_transaction = models.ForeignKey(
        'ledger.GlTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        db_table = 'deposit_transactions'
