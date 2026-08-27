"""
Tenant-aware Managers and QuerySets providing Defense-in-Depth (Rule 9).
"""
from django.db import models
from tenancy.context import get_current_tenant_id

class TenantAwareQuerySet(models.QuerySet):
    """
    QuerySet that automatically applies tenant filtering in addition to PostgreSQL RLS.
    """
    def filter_current_tenant(self):
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return self.filter(tenant_id=tenant_id)
        return self

class TenantManager(models.Manager.from_queryset(TenantAwareQuerySet)):
    """
    Default manager for all TenantModel instances.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return qs.filter(tenant_id=tenant_id)
        return qs
