"""
Root URL Configuration for Pharmaback SaaS API.
Source: https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI 3.0 Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Authentication & User Management
    path("api/auth/", include("apps.authentication.urls")),

    # SaaS Platform & Tenancy Management
    path("api/", include("tenancy.urls")),

    # Global Medicament Catalog (Public Reference)
    path("api/", include("apps.catalog.urls")),

    # Pharmacy Tenant Feature Modules
    path("api/pharmacy/inventory/", include("apps.inventory.urls")),
    path("api/pharmacy/pos/", include("apps.pos.urls")),
    path("api/pharmacy/customers/", include("apps.customers.urls")),
    path("api/pharmacy/suppliers/", include("apps.suppliers.urls")),
    path("api/pharmacy/billing/", include("apps.billing.urls")),
    path("api/pharmacy/", include("apps.billing.urls")),  # To support direct /api/pharmacy/financial-statement/
    path("api/pharmacy/", include("apps.suppliers.urls")), # To support direct /api/pharmacy/orders/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
