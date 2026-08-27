from django.contrib import admin
from apps.billing.models import ExpenseCategory, Expense

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "description")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "tenant", "amount", "payment_method", "date", "created_by", "created_at")
    list_filter = ("tenant", "payment_method", "date")
    search_fields = ("description", "category__name")
