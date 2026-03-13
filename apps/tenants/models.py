import uuid
from django.db import models
from apps.core_models import BaseModel, TenantModel


class CountryPack(models.Model):
    """Pluggable regulatory configuration per country."""
    country_code = models.CharField(max_length=2, primary_key=True)
    country_name = models.CharField(max_length=100)
    regulatory_authority = models.CharField(max_length=255)
    default_currency = models.CharField(max_length=3)
    data_protection_law = models.CharField(max_length=255, blank=True)
    data_localisation_required = models.BooleanField(default=False)
    aml_supervisory_body = models.CharField(max_length=255, blank=True)
    audit_retention_years = models.IntegerField(default=7)
    default_language = models.CharField(max_length=5, default='en')
    config = models.JSONField(default=dict, help_text='Full country pack configuration')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'country_packs'

    def __str__(self):
        return f"{self.country_name} ({self.country_code})"


class LicenceTier(BaseModel):
    """Licence types per country with feature flags and regulatory limits."""
    country = models.ForeignKey(CountryPack, on_delete=models.CASCADE, related_name='licence_tiers')
    tier_code = models.CharField(max_length=50)
    tier_name = models.CharField(max_length=255)
    can_accept_deposits = models.BooleanField(default=False)
    can_offer_savings = models.BooleanField(default=False)
    can_do_transfers = models.BooleanField(default=False)
    credit_only = models.BooleanField(default=False)
    min_capital_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    min_capital_currency = models.CharField(max_length=3, blank=True)
    car_requirement_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    single_obligor_limit_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    insider_lending_limit_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    REPORTING_FREQ_CHOICES = [('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly'), ('AD_HOC', 'Ad Hoc')]
    reporting_frequency = models.CharField(max_length=20, choices=REPORTING_FREQ_CHOICES, default='MONTHLY')
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'licence_tiers'
        unique_together = [('country', 'tier_code')]

    def __str__(self):
        return f"{self.country.country_code} - {self.tier_name}"


class Tenant(BaseModel):
    """Root entity — one per microfinance institution."""
    name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)
    country = models.ForeignKey(CountryPack, on_delete=models.PROTECT, related_name='tenants')
    licence_tier = models.ForeignKey(LicenceTier, on_delete=models.PROTECT, related_name='tenants')
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended'), ('TERMINATED', 'Terminated')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    subscription_active = models.BooleanField(default=True)
    default_currency = models.CharField(max_length=3)
    default_language = models.CharField(max_length=5, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    # White-label branding
    logo_url = models.TextField(blank=True)
    primary_brand_colour = models.CharField(max_length=7, blank=True)
    secondary_brand_colour = models.CharField(max_length=7, blank=True)
    custom_domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    tagline = models.CharField(max_length=255, blank=True)
    # Data protection
    data_localisation_required = models.BooleanField(default=False)
    data_centre_tag = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'tenants'

    def __str__(self):
        return self.trading_name or self.name


class RuleSetVersion(BaseModel):
    """Versioned regulatory rules — interest formulas, classification, provisioning."""
    country = models.ForeignKey(CountryPack, on_delete=models.CASCADE, related_name='rule_set_versions')
    RULE_TYPE_CHOICES = [
        ('INTEREST_FORMULA', 'Interest Formula'),
        ('LOAN_CLASSIFICATION', 'Loan Classification'),
        ('PROVISIONING', 'Provisioning'),
    ]
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    version_code = models.CharField(max_length=50)
    version_number = models.IntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    config = models.JSONField()
    approved_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_rule_sets'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    change_justification = models.TextField(blank=True)

    class Meta:
        db_table = 'rule_set_versions'
        unique_together = [('country', 'rule_type', 'version_code', 'version_number')]

    def __str__(self):
        return f"{self.version_code} v{self.version_number}"


class LicenceProfile(BaseModel):
    """Per-tenant licence identity card."""
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='licence_profile')
    licence_number = models.CharField(max_length=100, blank=True)
    licensing_authority = models.CharField(max_length=255, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    permitted_features = models.JSONField(default=dict)
    active_interest_formula = models.ForeignKey(
        RuleSetVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    active_classification = models.ForeignKey(
        RuleSetVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    active_provisioning = models.ForeignKey(
        RuleSetVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    aml_supervisory_body = models.CharField(max_length=255, blank=True)
    str_required = models.BooleanField(default=True)
    kyc_minimum_level = models.CharField(max_length=20, default='FULL_CDD')

    class Meta:
        db_table = 'licence_profiles'

    def __str__(self):
        return f"Licence: {self.tenant}"


class Branch(TenantModel):
    """Physical or logical branch of an MFI."""
    branch_code = models.CharField(max_length=20)
    branch_name = models.CharField(max_length=255)
    BRANCH_TYPE_CHOICES = [('URBAN', 'Urban'), ('PERI_URBAN', 'Peri-Urban'), ('RURAL', 'Rural')]
    branch_type = models.CharField(max_length=20, choices=BRANCH_TYPE_CHOICES, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'branches'
        unique_together = [('tenant', 'branch_code')]

    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"
