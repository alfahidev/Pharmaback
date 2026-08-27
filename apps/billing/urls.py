from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.billing.views import (
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    FinancialStatementView,
)

router = DefaultRouter()
router.register(r"expense-categories", ExpenseCategoryViewSet, basename="expense-categories")
router.register(r"expenses", ExpenseViewSet, basename="pharmacy-expenses")

urlpatterns = [
    path("financial-statement/", FinancialStatementView.as_view(), name="financial-statement"),
    path("", include(router.urls)),
]
