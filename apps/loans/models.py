from django.db import models
from apps.core_models import TenantModel, SyncModel


class LoanProduct(TenantModel):
    """Configurable loan product definitions per tenant."""
    product_code = models.CharField(max_length=20)
    product_name = models.CharField(max_length=255)
    PRODUCT_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual'), ('GROUP', 'Group'), ('SME', 'SME'),
        ('EMERGENCY', 'Emergency'), ('AGRICULTURAL', 'Agricultural'),
    ]
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    min_amount = models.DecimalField(max_digits=19, decimal_places=4)
    max_amount = models.DecimalField(max_digits=19, decimal_places=4)
    min_term_months = models.IntegerField()
    max_term_months = models.IntegerField()
    INTEREST_METHOD_CHOICES = [('FLAT', 'Flat'), ('REDUCING_BALANCE', 'Reducing Balance')]
    interest_method = models.CharField(max_length=20, choices=INTEREST_METHOD_CHOICES)
    default_interest_rate_pct = models.DecimalField(max_digits=7, decimal_places=4)
    origination_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    insurance_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    requires_collateral = models.BooleanField(default=False)
    requires_guarantor = models.BooleanField(default=False)
    LIABILITY_CHOICES = [('JOINT', 'Joint Liability'), ('INDIVIDUAL', 'Individual Liability')]
    group_liability_type = models.CharField(max_length=20, choices=LIABILITY_CHOICES, blank=True)
    allowed_frequencies = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'loan_products'
        unique_together = [('tenant', 'product_code')]

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"


class Loan(TenantModel, SyncModel):
    """Core loan record — tracks full lifecycle from application to close."""
    loan_number = models.CharField(max_length=50)
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='loans')
    group = models.ForeignKey('clients.Group', on_delete=models.SET_NULL, null=True, blank=True, related_name='loans')
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans')
    branch = models.ForeignKey('tenants.Branch', on_delete=models.PROTECT, related_name='loans')
    loan_officer = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='managed_loans')
    principal_amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3)
    interest_rate_pct = models.DecimalField(max_digits=7, decimal_places=4)
    interest_method = models.CharField(max_length=20)
    term_months = models.IntegerField()
    FREQ_CHOICES = [
        ('DAILY', 'Daily'), ('WEEKLY', 'Weekly'),
        ('FORTNIGHTLY', 'Fortnightly'), ('MONTHLY', 'Monthly'),
    ]
    repayment_frequency = models.CharField(max_length=20, choices=FREQ_CHOICES)
    origination_fee = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    insurance_fee = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total_interest = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    total_repayable = models.DecimalField(max_digits=19, decimal_places=4)
    outstanding_principal = models.DecimalField(max_digits=19, decimal_places=4)
    outstanding_interest = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    arrears_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    days_past_due = models.IntegerField(default=0)
    STATUS_CHOICES = [
        ('APPLICATION', 'Application'), ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'), ('DISBURSED', 'Disbursed'), ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'), ('WRITTEN_OFF', 'Written Off'), ('RESTRUCTURED', 'Restructured'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLICATION')
    CLASSIFICATION_CHOICES = [
        ('CURRENT', 'Current'), ('WATCH', 'Watch'), ('SUBSTANDARD', 'Substandard'),
        ('DOUBTFUL', 'Doubtful'), ('LOSS', 'Loss'),
    ]
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default='CURRENT')
    provision_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    provision_amount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    # Dates
    application_date = models.DateField()
    approval_date = models.DateField(null=True, blank=True)
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    first_repayment_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    # Approval chain
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    disbursed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    # Risk
    affordability_dti_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    collateral_description = models.TextField(blank=True)
    collateral_value = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    guarantor = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_insider_loan = models.BooleanField(default=False)
    override_flag = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    interest_formula_version = models.ForeignKey(
        'tenants.RuleSetVersion', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    is_test_data = models.BooleanField(default=False)

    class Meta:
        db_table = 'loans'
        unique_together = [('tenant', 'loan_number')]
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_loans_status'),
            models.Index(fields=['tenant', 'client'], name='idx_loans_client'),
            models.Index(fields=['tenant', 'classification'], name='idx_loans_class'),
        ]

    def __str__(self):
        return f"{self.loan_number} - {self.client}"


class RepaymentSchedule(TenantModel):
    """Expected repayment instalments — generated at disbursement."""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='schedule')
    instalment_number = models.IntegerField()
    due_date = models.DateField()
    principal_due = models.DecimalField(max_digits=19, decimal_places=4)
    interest_due = models.DecimalField(max_digits=19, decimal_places=4)
    fees_due = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total_due = models.DecimalField(max_digits=19, decimal_places=4)
    principal_paid = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    interest_paid = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    fees_paid = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total_paid = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    balance_after = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), ('PAID', 'Paid'), ('PARTIAL', 'Partial'), ('OVERDUE', 'Overdue'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    paid_date = models.DateField(null=True, blank=True)
    days_late = models.IntegerField(default=0)

    class Meta:
        db_table = 'repayment_schedules'
        unique_together = [('loan', 'instalment_number')]


class Repayment(TenantModel, SyncModel):
    """Actual payments received — offline-capable."""
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name='repayments')
    schedule = models.ForeignKey(RepaymentSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='repayments')
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3)
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'), ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'), ('CHEQUE', 'Cheque'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='+')
    received_at = models.DateTimeField()
    principal_applied = models.DecimalField(max_digits=19, decimal_places=4)
    interest_applied = models.DecimalField(max_digits=19, decimal_places=4)
    fees_applied = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    penalty_applied = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    receipt_number = models.CharField(max_length=50, blank=True)
    reversed = models.BooleanField(default=False)
    reversed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    gl_transaction = models.ForeignKey(
        'ledger.GlTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        db_table = 'repayments'
