from django.contrib import admin
from apps.customers.models import CustomerAccount, CustomerTransaction

class CustomerTransactionInline(admin.TabularInline):
    model = CustomerTransaction
    extra = 0
    readonly_fields = ("created_at", "balance_after")


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "tenant", "account_type", "current_balance", "credit_limit", "is_active")
    list_filter = ("tenant", "account_type", "is_active")
    search_fields = ("name", "phone")
    inlines = [CustomerTransactionInline]


@admin.register(CustomerTransaction)
class CustomerTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "tenant", "transaction_type", "payment_method", "amount", "balance_after", "created_at")
    list_filter = ("tenant", "transaction_type", "payment_method", "created_at")
    search_fields = ("customer__name", "note")
    readonly_fields = ("created_at",)
