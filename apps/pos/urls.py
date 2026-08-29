from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.pos.views import (
    POSScanView,
    POSTopProductsView,
    POSCheckoutView,
    CashSessionOpenView,
    CashSessionCloseView,
    CurrentCashSessionView,
    SaleViewSet,
    CashSessionViewSet,
)

router = DefaultRouter()
router.register(r"sales", SaleViewSet, basename="pos-sales")
router.register(r"sessions", CashSessionViewSet, basename="pos-sessions")

urlpatterns = [
    path("scan/", POSScanView.as_view(), name="pos-scan"),
    path("top-products/", POSTopProductsView.as_view(), name="pos-top-products"),
    path("checkout/", POSCheckoutView.as_view(), name="pos-checkout"),
    path("session/open/", CashSessionOpenView.as_view(), name="pos-session-open"),
    path("session/close/", CashSessionCloseView.as_view(), name="pos-session-close"),
    path("session/current/", CurrentCashSessionView.as_view(), name="pos-session-current"),
    path("", include(router.urls)),
]
