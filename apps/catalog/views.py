"""
Views for Global Medicament Catalog.
"""
from rest_framework import viewsets, permissions, filters
from drf_spectacular.utils import extend_schema
from apps.catalog.models import MedicamentCatalog
from apps.catalog.serializers import MedicamentCatalogSerializer
from tenancy.permissions import IsSaasOwner

class MedicamentCatalogViewSet(viewsets.ModelViewSet):
    """
    Global Medicament Catalog:
    - Read/Search: Accessible to all authenticated pharmacy staff.
    - Create/Update/Delete: Restricted to SaaS Owner / Superusers.
    """
    queryset = MedicamentCatalog.objects.filter(is_active=True)
    serializer_class = MedicamentCatalogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["barcode", "alternate_barcode", "name", "geo_code", "dci", "default_category"]
    ordering_fields = ["name", "barcode", "geo_code", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [IsSaasOwner()]
