"""
Serializers for Inventory, Batches, and Stock Movements.
"""
from rest_framework import serializers
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.catalog.serializers import MedicamentCatalogSerializer

class ProductBatchSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    months_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductBatch
        fields = [
            "id",
            "product",
            "batch_number",
            "expiration_date",
            "quantity_received",
            "quantity_current",
            "is_active",
            "is_expired",
            "is_expiring_soon",
            "months_until_expiry",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_expired",
            "is_expiring_soon",
            "months_until_expiry",
            "created_at",
            "updated_at",
        ]


class PharmacyProductSerializer(serializers.ModelSerializer):
    catalog_details = MedicamentCatalogSerializer(source="catalog_item", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    months_until_expiry = serializers.IntegerField(read_only=True)
    nearest_expiration_date = serializers.DateField(read_only=True)
    batches = ProductBatchSerializer(many=True, read_only=True)

    class Meta:
        model = PharmacyProduct
        fields = [
            "id",
            "barcode",
            "alternate_barcode",
            "name",
            "shelf_location",
            "purchase_price_ht",
            "selling_price",
            "tva_rate",
            "reorder_threshold",
            "is_active",
            "catalog_item",
            "catalog_details",
            "total_stock",
            "is_low_stock",
            "is_expiring_soon",
            "months_until_expiry",
            "nearest_expiration_date",
            "batches",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_stock",
            "is_low_stock",
            "is_expiring_soon",
            "months_until_expiry",
            "nearest_expiration_date",
            "batches",
            "created_at",
            "updated_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_barcode = serializers.CharField(source="product.barcode", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, default=None)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "product_barcode",
            "batch",
            "batch_number",
            "movement_type",
            "movement_type_display",
            "quantity",
            "reference_doc",
            "notes",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "product_name",
            "product_barcode",
            "batch_number",
            "created_by_username",
            "movement_type_display",
            "created_at",
        ]


class QuickRestockSerializer(serializers.Serializer):
    barcode = serializers.CharField(required=True, help_text="Code-barres principal ou code alternatif du produit")
    quantity = serializers.IntegerField(required=True, min_value=1, help_text="Quantité reçue à ajouter au stock")
    batch_number = serializers.CharField(required=False, allow_blank=True, default="", help_text="Numéro de lot (optionnel)")
    expiration_date = serializers.DateField(required=False, allow_null=True, help_text="Date de péremption (optionnelle)")
    purchase_price_ht = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, help_text="Prix d'achat unitaire HT actualisé")
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, help_text="Prix de vente unitaire TTC actualisé")

