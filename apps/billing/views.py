"""
Views for Expenses and Consolidated Financial Statements.
"""
from rest_framework import viewsets, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from common.viewsets import TenantModelViewSet, TenantAPIView
from apps.billing.models import ExpenseCategory, Expense
from apps.billing.serializers import ExpenseCategorySerializer, ExpenseSerializer
from apps.billing.services import calculate_financial_statement
from tenancy.permissions import IsAccountantOrAbove

class ExpenseCategoryViewSet(TenantModelViewSet):
    """
    Management of operational expense categories.
    """
    queryset = ExpenseCategory.objects.all().prefetch_related("expenses")
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAccountantOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering = ["name"]


class ExpenseViewSet(TenantModelViewSet):
    """
    Management and entry of operational expenses.
    """
    queryset = Expense.objects.all().select_related("category", "created_by")
    serializer_class = ExpenseSerializer
    permission_classes = [IsAccountantOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "category__name"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date", "-created_at"]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(tenant=user.pharmacy, created_by=user)


class FinancialStatementView(TenantAPIView):
    """
    Consolidated Financial Statement Endpoint:
    Calculates total sales, total expenses, net cashflow, gross margin,
    payment method breakdown, and customer debt exposure.
    """
    permission_classes = [IsAccountantOrAbove]

    @extend_schema(
        summary="État Financier Consolidé de l'Officine",
        description=(
            "Renvoie les indicateurs financiers consolidés (Total Ventes TTC/HT, Dépenses, "
            "Solde Net, Marge Brute estimée, Ventilation par mode de règlement et créances clients)."
        ),
        parameters=[
            OpenApiParameter(name="period", description="Période: 'today', 'week', 'month', 'custom'", required=False, type=str),
            OpenApiParameter(name="start_date", description="Date de début (YYYY-MM-DD) si période custom", required=False, type=str),
            OpenApiParameter(name="end_date", description="Date de fin (YYYY-MM-DD) si période custom", required=False, type=str),
            OpenApiParameter(name="payment_method", description="Filtrer par mode de paiement (ESPECE, WAVE, OMONEY...)", required=False, type=str),
        ],
        responses={200: OpenApiResponse(description="Bilan financier consolidé")}
    )
    def get(self, request):
        pharmacy = request.user.pharmacy
        if not pharmacy:
            return Response({"error": "Utilisateur non rattaché à une officine."}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get("period", "month")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        payment_method = request.query_params.get("payment_method")

        report = calculate_financial_statement(
            pharmacy=pharmacy,
            period=period,
            start_date=start_date,
            end_date=end_date,
            payment_method=payment_method,
        )
        return Response(report)
