"""
Inventory, FEFO Product Batches, and Stock Movements Models.
Row-Level Security Multi-Tenancy isolated.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.models import TenantModel
from apps.catalog.models import MedicamentCatalog

class PharmacyProduct(TenantModel):
    """
    Private pharmacy stock item. Isolated per tenant with PostgreSQL RLS.
    """
    catalog_item = models.ForeignKey(
        MedicamentCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pharmacy_products",
        verbose_name=_("Référence Catalogue National")
    )
    barcode = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name=_("Code-barres principal (Code 1)")
    )
    alternate_barcode = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Code-barres secondaire (Code 2)")
    )
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Désignation / Nom du produit"))
    shelf_location = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Emplacement / Code géo / Rayon")
    )
    purchase_price_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Prix unitaire d'achat HT (FCFA)")
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Prix unitaire de vente TTC (FCFA)")
    )
    tva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Taux TVA (%)")
    )
    reorder_threshold = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Seuil d'alerte réapprovisionnement")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Actif en vente"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_pharmacyproduct"
        verbose_name = _("Produit de l'Officine")
        verbose_name_plural = _("Produits de l'Officine")
        ordering = ["name"]
        constraints = [
            # Rule 14: Ensure barcode is unique per tenant
            models.UniqueConstraint(
                fields=["tenant", "barcode"],
                name="unique_tenant_product_barcode"
            )
        ]

    def __str__(self):
        return f"{self.name} [{self.barcode}]"

    @property
    def total_stock(self) -> int:
        """Sum of currently available positive quantity across non-expired batches."""
        batches = self.batches.filter(is_active=True, quantity_current__gt=0)
        return sum(batch.quantity_current for batch in batches)

    @property
    def is_low_stock(self) -> bool:
        """True if total current stock is less than or equal to reorder threshold."""
        return self.total_stock <= self.reorder_threshold

    @property
    def nearest_expiring_batch(self):
        """Returns the active batch with the earliest expiration date."""
        return self.batches.filter(is_active=True, quantity_current__gt=0).order_by("expiration_date").first()

    @property
    def nearest_expiration_date(self) -> date | None:
        batch = self.nearest_expiring_batch
        return batch.expiration_date if batch else None

    @property
    def is_expiring_soon(self) -> bool:
        """True if nearest batch expires within 90 days."""
        batch = self.nearest_expiring_batch
        if not batch:
            return False
        delta_days = (batch.expiration_date - date.today()).days
        return 0 <= delta_days <= 90

    @property
    def months_until_expiry(self) -> int | None:
        batch = self.nearest_expiring_batch
        if not batch:
            return None
        delta_days = (batch.expiration_date - date.today()).days
        return max(0, int(delta_days / 30))


class ProductBatch(TenantModel):
    """
    Physical product batch (Lot) enforcing FEFO (First Expired, First Out) inventory model.
    """
    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.CASCADE,
        related_name="batches",
        verbose_name=_("Produit")
    )
    batch_number = models.CharField(max_length=64, db_index=True, verbose_name=_("Numéro de lot"))
    expiration_date = models.DateField(db_index=True, verbose_name=_("Date de péremption"))
    quantity_received = models.IntegerField(default=0, verbose_name=_("Quantité initiale reçue"))
    quantity_current = models.IntegerField(default=0, verbose_name=_("Quantité actuelle disponible"))
    is_active = models.BooleanField(default=True, verbose_name=_("Lot actif"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_productbatch"
        verbose_name = _("Lot de Produit")
        verbose_name_plural = _("Lots de Produits")
        ordering = ["expiration_date", "id"]
        constraints = [
            # Rule 14: Unique batch number per product per tenant
            models.UniqueConstraint(
                fields=["tenant", "product", "batch_number"],
                name="unique_tenant_product_batch"
            )
        ]

    def clean(self):
        super().clean()
        # Rule 14: Verify product belongs to the exact same tenant
        if self.product_id and self.product.tenant_id != self.tenant_id:
            raise ValidationError(_("Le produit associé doit obligatoirement appartenir à la même officine."))

    def __str__(self):
        return f"Lot {self.batch_number} - {self.product.name} (Exp: {self.expiration_date})"

    @property
    def is_expired(self) -> bool:
        return self.expiration_date < date.today()

    @property
    def is_expiring_soon(self) -> bool:
        delta = (self.expiration_date - date.today()).days
        return 0 <= delta <= 90

    @property
    def months_until_expiry(self) -> int:
        delta = (self.expiration_date - date.today()).days
        return max(0, int(delta / 30))


class StockMovement(TenantModel):
    """
    Complete audit trail of all inventory additions, deductions, sales and losses.
    """
    MOVEMENT_TYPE_CHOICES = [
        ("IN_IMPORT", _("Importation initiale CSV")),
        ("IN_PURCHASE", _("Réception commande fournisseur")),
        ("OUT_SALE", _("Vente au comptoir (POS)")),
        ("ADJUSTMENT_IN", _("Ajustement inventaire positif")),
        ("ADJUSTMENT_OUT", _("Ajustement inventaire négatif")),
        ("LOSS_EXPIRED", _("Perte produit périmé")),
        ("LOSS_DAMAGED", _("Casse / Produit détérioré")),
        ("OUT_RETURN_SUPPLIER", _("Retour fournisseur")),
    ]

    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.CASCADE,
        related_name="stock_movements",
        verbose_name=_("Produit")
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
        verbose_name=_("Lot concerné")
    )
    movement_type = models.CharField(
        max_length=32,
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name=_("Type de mouvement")
    )
    quantity = models.IntegerField(verbose_name=_("Quantité (+/-)"))
    reference_doc = models.CharField(max_length=128, blank=True, default="", verbose_name=_("N° Pièce / Référence"))
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes / Motif"))
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Effectué par")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_stockmovement"
        verbose_name = _("Mouvement de Stock")
        verbose_name_plural = _("Mouvements de Stock")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.product_id and self.product.tenant_id != self.tenant_id:
            raise ValidationError(_("Le produit doit appartenir à la même officine."))
        if self.batch_id and self.batch.tenant_id != self.tenant_id:
            raise ValidationError(_("Le lot doit appartenir à la même officine."))
