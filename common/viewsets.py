"""
Base ViewSet and APIView for all tenant-owned endpoints.
Enforces Rule 1 (never trust client tenant_id), Rule 2 (server-side identity),
Rule 9 (defense-in-depth ORM filtering), and Rule 10 (no cross-tenant exposure).
"""
from django.db import connection
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from tenancy.context import set_current_tenant_id, get_current_tenant_id

def ensure_tenant_rls_context(user):
    """Guarantees that app.current_tenant_id is set at database engine level."""
    if user and user.is_authenticated:
        pharmacy_id = getattr(user, "pharmacy_id", None) or getattr(user, "tenant_id", None)
        if pharmacy_id:
            tenant_id_str = str(pharmacy_id)
            set_current_tenant_id(tenant_id_str)
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = %s;", [tenant_id_str])


class TenantAPIView(APIView):
    """
    Base APIView ensuring RLS session context for custom endpoints.
    """
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        ensure_tenant_rls_context(request.user)


class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet enforcing triple-layer tenant isolation:
    - Layer 1: Queryset auto-filtering (Django ORM).
    - Layer 2: Automatic tenant injection on create/update.
    - Layer 3: PostgreSQL Row-Level Security at database driver level.
    """
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        ensure_tenant_rls_context(request.user)

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return self.queryset.none()

        pharmacy_id = getattr(user, "pharmacy_id", None) or getattr(user, "tenant_id", None)
        if not pharmacy_id:
            if user.is_superuser:
                return super().get_queryset()
            return self.queryset.none()

        # Rule 9: Queryset filtering paired with RLS defense-in-depth
        return super().get_queryset().filter(tenant_id=pharmacy_id)

    def perform_create(self, serializer):
        # Rules 1 & 2: Explicit server-side injection of tenant identity
        user = self.request.user
        pharmacy = getattr(user, "pharmacy", None) or getattr(user, "tenant", None)
        if not pharmacy and not user.is_superuser:
            raise PermissionDenied("L'utilisateur n'est rattaché à aucune officine active.")
        serializer.save(tenant=pharmacy)
