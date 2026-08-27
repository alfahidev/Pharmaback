from django.contrib import admin
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement

class ProductBatchInline(admin.TabularInline):
    model = ProductBatch
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(PharmacyProduct)
class PharmacyProductAdmin(admin.ModelAdmin):
    list_display = ("name", "barcode", "alternate_barcode", "tenant", "selling_price", "shelf_location", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("name", "barcode", "alternate_barcode", "shelf_location")
    inlines = [ProductBatchInline]


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "product", "tenant", "expiration_date", "quantity_current", "is_active")
    list_filter = ("tenant", "expiration_date", "is_active")
    search_fields = ("batch_number", "product__name", "product__barcode")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "tenant", "movement_type", "quantity", "reference_doc", "created_by", "created_at")
    list_filter = ("tenant", "movement_type", "created_at")
    search_fields = ("product__name", "product__barcode", "reference_doc")
    readonly_fields = ("created_at",)
