"""
Transactional PostgreSQL Row-Level Security and SaaS Subscription Middlewares.
Enforces Rules 1, 2, 6, 7, and 8.
Source: https://docs.djangoproject.com/en/6.0/topics/http/middleware/
Source: https://docs.djangoproject.com/en/6.0/topics/db/transactions/
"""
import logging
from django.db import connection, transaction
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from tenancy.context import set_current_tenant_id, reset_current_tenant_id

logger = logging.getLogger(__name__)

def get_authenticated_user_from_request(request):
    """Retrieves authenticated user from standard session, test client, or token."""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    forced = getattr(request, "_force_auth_user", None)
    if forced and forced.is_authenticated:
        return forced
    return None


class TransactionalTenantRLSMiddleware:
    """
    Middleware establishing PostgreSQL Row-Level Security context for each HTTP request.

    Security Guarantees:
    - Never trusts tenant_id from client query parameters or request body (Rule 1).
    - Extracts tenant identity strictly from authenticated JWT / user session (Rule 2).
    - Uses transaction-scoped 'SET LOCAL' preventing connection-pool leakage (Rules 6 & 7).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _extract_tenant_id_from_request(self, request) -> str | None:
        user = get_authenticated_user_from_request(request)
        if user:
            tenant = getattr(user, "pharmacy", None) or getattr(user, "tenant", None)
            if tenant:
                return str(tenant.id)

        # DRF Bearer JWT header before DRF view dispatch
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ", 1)[1].strip()
            try:
                token = AccessToken(raw_token)
                tenant_id = token.payload.get("tenant_id")
                if tenant_id:
                    return str(tenant_id)
            except Exception:
                pass

        return None

    def __call__(self, request):
        tenant_id = self._extract_tenant_id_from_request(request)

        # Set Python thread/async context
        token = set_current_tenant_id(tenant_id)

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    if tenant_id:
                        # Rule 7: SET LOCAL is strictly scoped to the current transaction block
                        cursor.execute("SET LOCAL app.current_tenant_id = %s;", [tenant_id])
                    else:
                        cursor.execute("SET LOCAL app.current_tenant_id = '';")

                response = self.get_response(request)
                return response
        finally:
            reset_current_tenant_id(token)


class SubscriptionCheckMiddleware:
    """
    Middleware verifying that an authenticated Pharmacy tenant has an active subscription.
    SaaS Owner, Superusers, and whitelisted endpoints (auth, docs, subscription status) bypass this check.
    """

    EXEMPT_PATHS = (
        "/admin/",
        "/api/schema/",
        "/api/docs/",
        "/api/redoc/",
        "/api/auth/",
        "/api/saas/",
        "/api/pharmacy/subscription/status/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow exempt endpoints
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PATHS):
            return self.get_response(request)

        user = get_authenticated_user_from_request(request)
        if user:
            # Superusers and SAAS_OWNER have unrestricted access
            if getattr(user, "is_superuser", False) or getattr(user, "role", "") == "SAAS_OWNER":
                return self.get_response(request)

            pharmacy = getattr(user, "pharmacy", None)
            if pharmacy:
                # Refresh from db to get latest status in test environments
                subscription = getattr(pharmacy, "subscription", None)
                if subscription:
                    subscription.refresh_from_db()
                if not subscription or not subscription.is_currently_valid():
                    return JsonResponse(
                        {
                            "detail": "Abonnement de l'officine inactif, expiré ou suspendu. Veuillez contacter le propriétaire de la plateforme.",
                            "code": "SUBSCRIPTION_REQUIRED",
                            "pharmacy_id": str(pharmacy.id),
                            "pharmacy_name": pharmacy.name,
                            "subscription_status": subscription.status if subscription else "NONE",
                        },
                        status=403,
                    )

        return self.get_response(request)
