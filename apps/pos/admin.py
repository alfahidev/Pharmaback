from django.contrib import admin
from apps.pos.models import CashSession, Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("product", "batch", "quantity", "unit_price", "total_price")


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ("cashier", "tenant", "session_date", "initial_cash", "expected_cash", "actual_cash_counted", "cash_difference", "status")
    list_filter = ("tenant", "status", "session_date")
    search_fields = ("cashier__username", "notes")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "tenant", "cashier", "payment_method", "total_ttc", "status", "created_at")
    list_filter = ("tenant", "payment_method", "status", "created_at")
    search_fields = ("ticket_number", "customer__name", "cashier__username")
    inlines = [SaleItemInline]
    readonly_fields = ("ticket_number", "created_at")
