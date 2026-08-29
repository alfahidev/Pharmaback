"""
Serializers for Wholesaler Suppliers, Purchase Orders, and Claims.
"""
from rest_framework import serializers
from apps.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierClaim
from apps.inventory.serializers import PharmacyProductSerializer

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "phone",
            "address",
            "contact_person",
            "order_website_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_barcode = serializers.CharField(source="product.barcode", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_barcode",
            "quantity_ordered",
            "quantity_received",
            "unit_purchase_price",
        ]
        read_only_fields = ["id", "product_name", "product_barcode"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "order_number",
            "status",
            "status_display",
            "total_amount_ht",
            "notes",
            "created_by",
            "created_by_username",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "supplier_name",
            "status_display",
            "created_by_username",
            "items",
            "created_at",
            "updated_at",
        ]


class PurchaseOrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_ordered = serializers.IntegerField(min_value=1)
    unit_purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = PurchaseOrderItemInputSerializer(many=True)


class SupplierClaimSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True, default=None)
    claim_type_display = serializers.CharField(source="get_claim_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = SupplierClaim
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "order",
            "order_number",
            "claim_type",
            "claim_type_display",
            "product_name",
            "batch_number",
            "quantity_affected",
            "description",
            "photo_proof",
            "status",
            "status_display",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "supplier_name",
            "order_number",
            "claim_type_display",
            "status_display",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
