from rest_framework import serializers
from apps.catalog.models import MedicamentCatalog

class MedicamentCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentCatalog
        fields = [
            "id",
            "barcode",
            "name",
            "dci",
            "form_dosage",
            "default_category",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
