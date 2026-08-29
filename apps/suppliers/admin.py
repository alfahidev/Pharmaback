from django.contrib import admin
from apps.suppliers.models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "contact_person", "tenant", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("name", "phone", "contact_person")
