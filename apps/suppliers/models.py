"""
Suppliers, Wholesaler Purchase Orders, and Delivery Claims.
Row-Level Security Multi-Tenancy isolated.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.models import TenantModel
from apps.inventory.models import PharmacyProduct
from common.utils import generate_ticket_number

class Supplier(TenantModel):
    """
    Wholesaler / Pharmaceutical supplier (e.g. Laborex, Cophase, Sodipharm...).
    """
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Nom du grossiste / Fournisseur"))
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name=_("Téléphone"))
    address = models.TextField(blank=True, default="", verbose_name=_("Adresse"))
    contact_person = models.CharField(max_length=128, blank=True, default="", verbose_name=_("Nom du délégué / contact"))
    order_website_url = models.URLField(blank=True, default="", verbose_name=_("Portail de commande en ligne"))
    is_active = models.BooleanField(default=True, verbose_name=_("Fournisseur actif"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers_supplier"
        verbose_name = _("Fournisseur Grossiste")
        verbose_name_plural = _("Fournisseurs Grossistes")
        ordering = ["name"]

    def __str__(self):
        return self.name


def generate_order_number() -> str:
    return generate_ticket_number("CMD")


class PurchaseOrder(TenantModel):
    """
    Replenishment purchase order sent to a wholesaler.
    """
    STATUS_CHOICES = [
        ("DRAFT", _("Brouillon / Proposition")),
        ("EXPORTED", _("Exporté / Envoyé au grossiste")),
        ("RECEIVED", _("Livré & Réceptionné")),
        ("CANCELLED", _("Commande Annulée")),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Fournisseur Grossiste")
    )
    order_number = models.CharField(
        max_length=64,
        db_index=True,
        default=generate_order_number,
        verbose_name=_("Numéro de Commande")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="DRAFT",
        db_index=True,
        verbose_name=_("Statut")
    )
    total_amount_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Montant total estimé HT (FCFA)")
    )
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes / Instructions"))
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers_purchaseorder"
        verbose_name = _("Bon de Commande Fournisseur")
        verbose_name_plural = _("Bons de Commande Fournisseurs")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "order_number"],
                name="unique_tenant_purchase_order"
            )
        ]

    def clean(self):
        super().clean()
        if self.supplier_id and self.supplier.tenant_id != self.tenant_id:
            raise ValidationError(_("Le fournisseur doit appartenir à la même officine."))

    def __str__(self):
        return f"Commande {self.order_number} - {self.supplier.name} ({self.get_status_display()})"


class PurchaseOrderItem(TenantModel):
    """
    Individual medication item line on a purchase order.
    """
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Bon de commande")
    )
    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name=_("Produit")
    )
    quantity_ordered = models.PositiveIntegerField(verbose_name=_("Quantité commandée"))
    quantity_received = models.PositiveIntegerField(default=0, verbose_name=_("Quantité reçue"))
    unit_purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Prix unitaire d'achat HT (FCFA)")
    )

    class Meta:
        db_table = "suppliers_purchaseorderitem"
        verbose_name = _("Ligne de Commande Fournisseur")
        verbose_name_plural = _("Lignes de Commande Fournisseur")
        ordering = ["id"]

    def clean(self):
        super().clean()
        if self.order_id and self.order.tenant_id != self.tenant_id:
            raise ValidationError(_("La commande doit appartenir à la même officine."))
        if self.product_id and self.product.tenant_id != self.tenant_id:
            raise ValidationError(_("Le produit doit appartenir à la même officine."))

    def __str__(self):
        return f"{self.product.name} x {self.quantity_ordered} ({self.order.order_number})"


class SupplierClaim(TenantModel):
    """
    Delivery incident / dispute ticket for wrong, missing, or expired products from a supplier.
    """
    CLAIM_TYPE_CHOICES = [
        ("EXPIRED_RECEIVED", _("Produit reçu périmé ou proche péremption")),
        ("MISSING_ITEM", _("Produit facturé mais manquant")),
        ("WRONG_PRODUCT", _("Erreur de produit livré (Non conforme)")),
        ("DAMAGED", _("Produit cassé / Emballage détérioré")),
    ]

    STATUS_CHOICES = [
        ("PENDING", _("En attente de traitement")),
        ("ACCEPTED", _("Réclamation acceptée par le grossiste")),
        ("REFUNDED", _("Avoir / Remboursement émis")),
        ("REJECTED", _("Réclamation rejetée")),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="claims",
        verbose_name=_("Fournisseur concerné")
    )
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
        verbose_name=_("Commande liée (optionnelle)")
    )
    claim_type = models.CharField(
        max_length=32,
        choices=CLAIM_TYPE_CHOICES,
        verbose_name=_("Motif de réclamation")
    )
    product_name = models.CharField(max_length=255, verbose_name=_("Nom du produit concerné"))
    batch_number = models.CharField(max_length=64, blank=True, default="", verbose_name=_("N° de lot concerné"))
    quantity_affected = models.PositiveIntegerField(verbose_name=_("Quantité défectueuse / manquante"))
    description = models.TextField(verbose_name=_("Explication détaillée du litige"))
    photo_proof = models.ImageField(
        upload_to="claim_proofs/",
        null=True,
        blank=True,
        verbose_name=_("Photo justificative")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
        verbose_name=_("Statut du litige")
    )
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Déclaré par")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers_supplierclaim"
        verbose_name = _("Réclamation Fournisseur")
        verbose_name_plural = _("Réclamations Fournisseurs")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.supplier_id and self.supplier.tenant_id != self.tenant_id:
            raise ValidationError(_("Le fournisseur doit appartenir à la même officine."))
        if self.order_id and self.order.tenant_id != self.tenant_id:
            raise ValidationError(_("La commande doit appartenir à la même officine."))

    def __str__(self):
        return f"Litige {self.get_claim_type_display()} - {self.supplier.name} ({self.product_name})"
