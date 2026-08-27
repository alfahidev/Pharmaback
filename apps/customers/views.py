"""
Views for Customer Accounts and Credit Transactions.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from common.viewsets import TenantModelViewSet
from apps.customers.models import CustomerAccount, CustomerTransaction
from apps.customers.serializers import (
    CustomerAccountSerializer,
    CustomerTransactionSerializer,
    CustomerDepositSerializer,
)

class CustomerAccountViewSet(TenantModelViewSet):
    """
    Endpoints for customer accounts, deposits and credit lines.
    """
    queryset = CustomerAccount.objects.all().prefetch_related("transactions")
    serializer_class = CustomerAccountSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "phone", "email"]
    ordering_fields = ["name", "current_balance", "created_at"]
    ordering = ["name"]

    @extend_schema(
        summary="Effectuer un versement / acompte sur compte client",
        request=CustomerDepositSerializer,
        responses={200: CustomerAccountSerializer}
    )
    @action(detail=True, methods=["post"], url_path="deposit")
    def deposit(self, request, pk=None):
        customer = self.get_object()
        serializer = CustomerDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]
        payment_method = serializer.validated_data["payment_method"]
        note = serializer.validated_data.get("note", "Versement acompte")

        with transaction.atomic():
            # Update customer balance
            customer.current_balance += amount
            customer.save()

            # Record ledger transaction
            CustomerTransaction.objects.create(
                tenant=customer.tenant,
                customer=customer,
                transaction_type="DEPOSIT",
                payment_method=payment_method,
                amount=amount,
                balance_after=customer.current_balance,
                note=note,
                created_by=request.user,
            )

        return Response(CustomerAccountSerializer(customer).data)

    @extend_schema(
        summary="Relevé mensuel du compte client",
        responses={200: OpenApiResponse(description="Relevé mensuel des opérations et état de la dette")}
    )
    @action(detail=True, methods=["get"], url_path="statement")
    def statement(self, request, pk=None):
        customer = self.get_object()
        month_param = request.query_params.get("month")  # YYYY-MM
        transactions_qs = customer.transactions.all()

        if month_param:
            try:
                year, month = map(int, month_param.split("-"))
                transactions_qs = transactions_qs.filter(created_at__year=year, created_at__month=month)
            except ValueError:
                pass

        total_deposits = sum(
            t.amount for t in transactions_qs if t.transaction_type in ("DEPOSIT", "PAYMENT_CREDIT", "REFUND")
        )
        total_purchases = sum(
            t.amount for t in transactions_qs if t.transaction_type == "PURCHASE"
        )

        return Response({
            "customer_id": customer.id,
            "customer_name": customer.name,
            "phone": customer.phone,
            "account_type": customer.account_type,
            "current_balance": str(customer.current_balance),
            "credit_limit": str(customer.credit_limit),
            "total_deposits_period": str(total_deposits),
            "total_purchases_period": str(total_purchases),
            "transactions": CustomerTransactionSerializer(transactions_qs, many=True).data,
        })


class CustomerTransactionViewSet(TenantModelViewSet):
    """
    Read-only view of customer account transactions.
    """
    queryset = CustomerTransaction.objects.all().select_related("customer", "sale", "created_by")
    serializer_class = CustomerTransactionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["customer__name", "customer__phone", "note"]
    ordering_fields = ["created_at", "amount"]
    ordering = ["-created_at"]
