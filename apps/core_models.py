"""
Base model mixins for the Pan-African Microfinance SaaS platform.
All tenant-scoped models inherit from TenantModel.
All offline-capable models also inherit from SyncModel.
"""
import uuid
from django.db import models


class BaseModel(models.Model):
    """Abstract base with UUID PK and timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(BaseModel):
    """Abstract base for all tenant-scoped models. RLS enforces isolation."""
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='%(class)s_set', db_index=True
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Mixin for soft-deletable models."""
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class SyncModel(models.Model):
    """Mixin for offline-capable models with sync support."""
    sync_id = models.UUIDField(default=uuid.uuid4, editable=False)
    sync_status = models.CharField(
        max_length=20, default='SYNCED',
        choices=[
            ('SYNCED', 'Synced'),
            ('PENDING_UPLOAD', 'Pending Upload'),
            ('CONFLICT', 'Conflict'),
            ('REJECTED', 'Rejected'),
        ]
    )
    device_id = models.CharField(max_length=100, null=True, blank=True)
    client_created_at = models.DateTimeField(null=True, blank=True)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    server_confirmed_at = models.DateTimeField(null=True, blank=True)
    conflict_data = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True
