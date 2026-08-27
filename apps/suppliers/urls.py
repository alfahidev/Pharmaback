from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.suppliers.views import SupplierViewSet, PurchaseOrderViewSet, SupplierClaimViewSet

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="pharmacy-suppliers")
router.register(r"orders", PurchaseOrderViewSet, basename="pharmacy-orders")
router.register(r"claims", SupplierClaimViewSet, basename="pharmacy-claims")

urlpatterns = [
    path("", include(router.urls)),
]
