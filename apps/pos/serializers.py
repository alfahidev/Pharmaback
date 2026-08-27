"""
Serializers for Point of Sale (POS), Fast Barcode Scanning, and Cash Sessions.
"""
from decimal import Decimal
from rest_framework import serializers
from apps.pos.models import CashSession, Sale, SaleItem
from apps.customers.serializers import CustomerAccountSerializer

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_barcode = serializers.CharField(source="product.barcode", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, default=None)
    expiration_date = serializers.DateField(source="batch.expiration_date", read_only=True, default=None)

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_barcode",
            "batch",
            "batch_number",
            "expiration_date",
            "quantity",
            "unit_price",
            "total_price",
        ]
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    cashier_username = serializers.CharField(source="cashier.username", read_only=True, default="")
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id",
            "ticket_number",
            "cash_session",
            "cashier",
            "cashier_username",
            "customer",
            "customer_name",
            "total_ht",
            "total_tva",
            "total_ttc",
            "payment_method",
            "payment_method_display",
            "amount_received",
            "change_returned",
            "status",
            "status_display",
            "items",
            "created_at",
        ]
        read_only_fields = fields


class CashSessionSerializer(serializers.ModelSerializer):
    cashier_username = serializers.CharField(source="cashier.username", read_only=True)
    total_sales_count = serializers.IntegerField(source="sales.count", read_only=True)

    class Meta:
        model = CashSession
        fields = [
            "id",
            "cashier",
            "cashier_username",
            "session_date",
            "opened_at",
            "closed_at",
            "initial_cash",
            "expected_cash",
            "actual_cash_counted",
            "cash_difference",
            "status",
            "notes",
            "total_sales_count",
        ]
        read_only_fields = [
            "id",
            "cashier_username",
            "opened_at",
            "closed_at",
            "cash_difference",
            "total_sales_count",
        ]


class CashSessionOpenSerializer(serializers.Serializer):
    initial_cash = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CashSessionCloseSerializer(serializers.Serializer):
    actual_cash_counted = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class POSScanResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    barcode = serializers.CharField()
    alternate_barcode = serializers.CharField(allow_blank=True)
    name = serializers.CharField()
    shelf_location = serializers.CharField(allow_blank=True)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_stock = serializers.IntegerField()
    is_low_stock = serializers.BooleanField()
    is_expiring_soon = serializers.BooleanField()
    months_until_expiry = serializers.IntegerField(allow_null=True)
    nearest_expiration_date = serializers.DateField(allow_null=True)


class CheckoutItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class CheckoutRequestSerializer(serializers.Serializer):
    items = CheckoutItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=Sale.PAYMENT_METHOD_CHOICES,
        default="ESPECE"
    )
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    amount_received = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    session_id = serializers.IntegerField(required=False, allow_null=True)
