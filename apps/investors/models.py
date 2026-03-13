from django.db import models
from apps.core_models import TenantModel


class InvestorProfile(TenantModel):
    """Investor/funder linked to a user account."""
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='investor_profiles')
    investor_name = models.CharField(max_length=255)
    INVESTOR_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual'), ('INSTITUTIONAL', 'Institutional'), ('FUND', 'Fund'),
    ]
    investor_type = models.CharField(max_length=20, choices=INVESTOR_TYPE_CHOICES)
    investment_currency = models.CharField(max_length=3)
    invested_amount = models.DecimalField(max_digits=19, decimal_places=4)
    invested_amount_local = models.DecimalField(max_digits=19, decimal_places=4)
    investment_date = models.DateField()
    exchange_rate_at_investment = models.DecimalField(max_digits=19, decimal_places=8)
    current_value_local = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended'), ('EXITED', 'Exited')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    covenant_thresholds = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'investor_profiles'

    def __str__(self):
        return f"{self.investor_name} ({self.investment_currency})"


class InvestorShareLink(TenantModel):
    """Time-limited and/or password-protected shareable dashboard link."""
    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='share_links'
    )
    token = models.CharField(max_length=128, unique=True)
    password_hash = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_views = models.IntegerField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'investor_share_links'


class Dividend(TenantModel):
    """Dividend declarations and payments to investors."""
    investor = models.ForeignKey(InvestorProfile, on_delete=models.PROTECT, related_name='dividends')
    period = models.CharField(max_length=20)
    declared_rate_pct = models.DecimalField(max_digits=7, decimal_places=4)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3)
    STATUS_CHOICES = [
        ('DECLARED', 'Declared'), ('APPROVED', 'Approved'),
        ('PAID', 'Paid'), ('REINVESTED', 'Reinvested'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DECLARED')
    paid_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'dividends'
