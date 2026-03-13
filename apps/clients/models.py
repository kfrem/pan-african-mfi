from django.db import models
from apps.core_models import TenantModel, SoftDeleteModel, SyncModel


class Client(TenantModel, SoftDeleteModel, SyncModel):
    """Borrower/depositor — the core customer record."""
    branch = models.ForeignKey('tenants.Branch', on_delete=models.PROTECT, related_name='clients')
    CLIENT_TYPE_CHOICES = [('INDIVIDUAL', 'Individual'), ('SME', 'SME'), ('GROUP', 'Group')]
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES)
    client_number = models.CharField(max_length=50)
    full_legal_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    GENDER_CHOICES = [('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    # Identity
    national_id_type = models.CharField(max_length=50, blank=True)
    national_id_number = models.CharField(max_length=100, blank=True)
    id_issue_date = models.DateField(null=True, blank=True)
    id_expiry_date = models.DateField(null=True, blank=True)
    # Contact
    phone_primary = models.CharField(max_length=20, blank=True)
    phone_secondary = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    # Address
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, blank=True)
    # Financial
    occupation = models.CharField(max_length=100, blank=True)
    employer_name = models.CharField(max_length=255, blank=True)
    monthly_income = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    income_currency = models.CharField(max_length=3, blank=True)
    source_of_funds = models.CharField(max_length=255, blank=True)
    # Risk & compliance
    RISK_CHOICES = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')]
    risk_rating = models.CharField(max_length=10, choices=RISK_CHOICES, default='LOW')
    is_pep = models.BooleanField(default=False, verbose_name='Politically Exposed Person')
    is_insider = models.BooleanField(default=False)
    insider_relationship = models.CharField(max_length=100, blank=True)
    KYC_STATUS_CHOICES = [
        ('INCOMPLETE', 'Incomplete'), ('COMPLETE', 'Complete'),
        ('VERIFIED', 'Verified'), ('EXPIRED', 'Expired'),
    ]
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='INCOMPLETE')
    kyc_verified_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    sanctions_checked = models.BooleanField(default=False)
    sanctions_hit = models.BooleanField(default=False)
    onboarding_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    # Assignment
    assigned_officer = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_clients'
    )
    is_test_data = models.BooleanField(default=False)

    class Meta:
        db_table = 'clients'
        unique_together = [('tenant', 'client_number')]
        indexes = [
            models.Index(fields=['tenant', 'branch'], name='idx_clients_branch'),
            models.Index(fields=['tenant', 'assigned_officer'], name='idx_clients_officer'),
        ]

    def __str__(self):
        return f"{self.full_legal_name} ({self.client_number})"


class Group(TenantModel, SyncModel):
    """Solidarity/group lending entity."""
    branch = models.ForeignKey('tenants.Branch', on_delete=models.PROTECT, related_name='groups')
    group_name = models.CharField(max_length=255)
    group_number = models.CharField(max_length=50)
    leader = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_groups')
    FREQ_CHOICES = [('WEEKLY', 'Weekly'), ('BIWEEKLY', 'Biweekly'), ('MONTHLY', 'Monthly')]
    meeting_frequency = models.CharField(max_length=20, choices=FREQ_CHOICES, blank=True)
    meeting_day = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'groups'
        unique_together = [('tenant', 'group_number')]

    def __str__(self):
        return f"{self.group_name} ({self.group_number})"


class GroupMember(models.Model):
    """Link table: clients in groups."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='group_memberships')
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'group_members'
        unique_together = [('group', 'client')]


class KycDocument(TenantModel, SyncModel):
    """KYC document uploads stored in Supabase Storage."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='kyc_documents')
    DOC_TYPE_CHOICES = [
        ('ID_SCAN', 'ID Scan'), ('PROOF_OF_ADDRESS', 'Proof of Address'),
        ('PHOTO', 'Photo'), ('SOURCE_OF_FUNDS', 'Source of Funds'), ('EDD_REPORT', 'EDD Report'),
    ]
    document_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES)
    file_path = models.TextField(help_text='Supabase Storage path')
    file_name = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_documents'
