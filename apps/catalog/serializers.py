from rest_framework import serializers
from apps.catalog.models import MedicamentCatalog

class MedicamentCatalogSerializer(serializers.ModelSerializer):
    alternate_barcode = serializers.CharField(required=False, allow_blank=True, default="")
    geo_code = serializers.CharField(required=False, allow_blank=True, default="")
    default_category = serializers.CharField(required=False, allow_blank=True, default="")
    dci = serializers.CharField(required=False, allow_blank=True, default="")
    form_dosage = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = MedicamentCatalog
        fields = [
            "id",
            "barcode",
            "alternate_barcode",
            "geo_code",
            "name",
            "dci",
            "form_dosage",
            "default_category",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
