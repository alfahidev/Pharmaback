from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tenancy.views import (
    SaasTenantViewSet,
    SaasPlanViewSet,
    SaasStatsView,
    PharmacySubscriptionStatusView,
    PharmacyProfileView,
)

router = DefaultRouter()
router.register(r"saas/tenants", SaasTenantViewSet, basename="saas-tenants")
router.register(r"saas/plans", SaasPlanViewSet, basename="saas-plans")

urlpatterns = [
    path("saas/stats/", SaasStatsView.as_view(), name="saas-stats"),
    path("", include(router.urls)),
    path("pharmacy/subscription/status/", PharmacySubscriptionStatusView.as_view(), name="pharmacy-subscription-status"),
    path("pharmacy/profile/", PharmacyProfileView.as_view(), name="pharmacy-profile"),
]
