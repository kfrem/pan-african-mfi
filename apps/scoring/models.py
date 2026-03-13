from django.db import models
from apps.core_models import TenantModel


class CreditScoreModel(TenantModel):
    """Configurable credit scoring model per tenant with weighted criteria."""
    model_name = models.CharField(max_length=100)
    model_version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    criteria = models.JSONField(help_text='Array of scoring criteria with weights')
    score_ranges = models.JSONField(default=list, help_text='Score ranges with labels and recommendations')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'credit_score_models'
        unique_together = [('tenant', 'model_name', 'model_version')]

    def __str__(self):
        return f"{self.model_name} v{self.model_version}"


class ClientCreditScore(TenantModel):
    """Computed credit score for a client — with override capability."""
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='credit_scores')
    model = models.ForeignKey(CreditScoreModel, on_delete=models.PROTECT, related_name='scores')
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    risk_label = models.CharField(max_length=20)
    recommendation = models.CharField(max_length=30)
    component_scores = models.JSONField(help_text='Breakdown by criteria')
    computed_at = models.DateTimeField(auto_now_add=True)
    CONTEXT_CHOICES = [
        ('LOAN_APPLICATION', 'Loan Application'),
        ('PERIODIC_REVIEW', 'Periodic Review'),
        ('MANUAL', 'Manual'),
    ]
    computed_for = models.CharField(max_length=20, choices=CONTEXT_CHOICES, blank=True)
    loan = models.ForeignKey('loans.Loan', on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_scores')
    # Override
    overridden = models.BooleanField(default=False)
    override_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    override_reason = models.TextField(blank=True)
    overridden_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    overridden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'client_credit_scores'
        indexes = [
            models.Index(fields=['tenant', 'client', '-computed_at'], name='idx_scores_client'),
        ]
