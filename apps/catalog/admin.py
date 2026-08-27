from django.contrib import admin
from apps.catalog.models import MedicamentCatalog

@admin.register(MedicamentCatalog)
class MedicamentCatalogAdmin(admin.ModelAdmin):
    list_display = ("barcode", "name", "dci", "form_dosage", "default_category", "is_active")
    list_filter = ("default_category", "is_active")
    search_fields = ("barcode", "name", "dci")
