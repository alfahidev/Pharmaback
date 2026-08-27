from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventory.views import (
    PharmacyProductViewSet,
    ProductBatchViewSet,
    StockMovementViewSet,
    InventoryCSVImportView,
    InventoryCSVExportView,
)

router = DefaultRouter()
router.register(r"products", PharmacyProductViewSet, basename="pharmacy-products")
router.register(r"batches", ProductBatchViewSet, basename="pharmacy-batches")
router.register(r"movements", StockMovementViewSet, basename="pharmacy-movements")

urlpatterns = [
    path("import-csv/", InventoryCSVImportView.as_view(), name="inventory-import-csv"),
    path("export-csv/", InventoryCSVExportView.as_view(), name="inventory-export-csv"),
    path("", include(router.urls)),
]
