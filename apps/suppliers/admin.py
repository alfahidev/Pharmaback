from django.contrib import admin
from apps.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierClaim

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "tenant", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("name", "phone")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "tenant", "status", "total_amount_ht", "created_at")
    list_filter = ("tenant", "status", "created_at")
    search_fields = ("order_number", "supplier__name")
    inlines = [PurchaseOrderItemInline]


@admin.register(SupplierClaim)
class SupplierClaimAdmin(admin.ModelAdmin):
    list_display = ("product_name", "supplier", "tenant", "claim_type", "quantity_affected", "status", "created_at")
    list_filter = ("tenant", "claim_type", "status", "created_at")
    search_fields = ("product_name", "batch_number", "supplier__name", "description")
