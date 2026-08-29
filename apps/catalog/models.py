"""
Global Medicament Catalog (Public/Shared national repository).
Not tenant-scoped; accessible across all pharmacies for standard identification.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

class MedicamentCatalog(models.Model):
    """
    Standardized national reference database for medicines and healthcare products.
    Shared globally across all tenant pharmacies.
    """
    barcode = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name=_("Code 1 / Code-barres principal (EAN-13/CIP)")
    )
    alternate_barcode = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Code 2 / Code alternatif")
    )
    geo_code = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Code géo / Rayon indicatif")
    )
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Label / Nom commercial"))
    dci = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("DCI (Dénomination Commune Internationale)")
    )
    form_dosage = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Forme galénique & Dosage")
    )
    default_category = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Famille thérapeutique (Optionnelle)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Actif au catalogue"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medicament_catalog"
        verbose_name = _("Médicament du Catalogue National")
        verbose_name_plural = _("Catalogue National des Médicaments")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.barcode})"
