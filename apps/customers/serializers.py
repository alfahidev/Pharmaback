"""
Serializers for Customer Accounts and Credit Transactions.
"""
from decimal import Decimal
from rest_framework import serializers
from apps.customers.models import CustomerAccount, CustomerTransaction

class CustomerTransactionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = CustomerTransaction
        fields = [
            "id",
            "customer",
            "sale",
            "transaction_type",
            "transaction_type_display",
            "payment_method",
            "payment_method_display",
            "amount",
            "balance_after",
            "note",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "balance_after",
            "created_by_username",
            "transaction_type_display",
            "payment_method_display",
            "created_at",
        ]


class CustomerAccountSerializer(serializers.ModelSerializer):
    available_credit = serializers.SerializerMethodField()
    recent_transactions = CustomerTransactionSerializer(source="transactions", many=True, read_only=True)

    class Meta:
        model = CustomerAccount
        fields = [
            "id",
            "name",
            "phone",
            "account_type",
            "current_balance",
            "credit_limit",
            "available_credit",
            "is_active",
            "recent_transactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "available_credit", "recent_transactions", "created_at", "updated_at"]

    def get_available_credit(self, obj) -> str:
        return f"{obj.current_balance + obj.credit_limit:.2f}"


class CustomerDepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    payment_method = serializers.ChoiceField(
        choices=CustomerTransaction.PAYMENT_METHOD_CHOICES,
        default="ESPECE"
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")
