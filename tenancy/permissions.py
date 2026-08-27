"""
Role and Tenancy DRF Permissions.
"""
from rest_framework.permissions import BasePermission

class IsSaasOwner(BasePermission):
    """Allows access only to SaaS platform owners / superusers."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, "role", "") == "SAAS_OWNER")
        )


class IsTenantAdmin(BasePermission):
    """Allows access only to Pharmacy Owners/Titular Admins."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or getattr(request.user, "role", "") in ("ADMIN", "TITULAIRE", "SAAS_OWNER")
            )
        )


class IsTenantStaff(BasePermission):
    """Allows access to authenticated members belonging to a pharmacy tenant."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, "pharmacy_id", None) or request.user.is_superuser)
        )


class IsCashierOrAbove(BasePermission):
    """Allows access to POS cashiers, pharmacists, and admins."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "role", "") in ("CAISSIER", "PHARMACIEN", "ADMIN", "TITULAIRE", "SAAS_OWNER")
                or request.user.is_superuser
            )
        )


class IsPharmacistOrAbove(BasePermission):
    """Allows access to Pharmacists and Admins (Stock management, Orders, Claims)."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "role", "") in ("PHARMACIEN", "ADMIN", "TITULAIRE", "SAAS_OWNER")
                or request.user.is_superuser
            )
        )


class IsAccountantOrAbove(BasePermission):
    """Allows access to Accountants, Financial managers, and Admins."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "role", "") in ("COMPTABLE", "ADMIN", "TITULAIRE", "SAAS_OWNER")
                or request.user.is_superuser
            )
        )
