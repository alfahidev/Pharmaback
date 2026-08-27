from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.catalog.views import MedicamentCatalogViewSet

router = DefaultRouter()
router.register(r"catalog", MedicamentCatalogViewSet, basename="medicament-catalog")

urlpatterns = [
    path("", include(router.urls)),
]
