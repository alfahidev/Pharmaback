"""
Serializers for Expenses, Categories, and Financial Statements.
"""
from rest_framework import serializers
from apps.billing.models import ExpenseCategory, Expense

class ExpenseCategorySerializer(serializers.ModelSerializer):
    expenses_count = serializers.IntegerField(source="expenses.count", read_only=True)

    class Meta:
        model = ExpenseCategory
        fields = [
            "id",
            "name",
            "description",
            "expenses_count",
            "created_at",
        ]
        read_only_fields = ["id", "expenses_count", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    receipt_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "amount",
            "payment_method",
            "payment_method_display",
            "description",
            "receipt_file",
            "date",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "payment_method_display",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
