from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.customers.views import CustomerAccountViewSet, CustomerTransactionViewSet

router = DefaultRouter()
router.register(r"accounts", CustomerAccountViewSet, basename="customer-accounts")
router.register(r"transactions", CustomerTransactionViewSet, basename="customer-transactions")

urlpatterns = [
    path("", include(router.urls)),
]
