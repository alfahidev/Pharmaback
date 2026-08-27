"""
Point of Sale (POS), Daily Cash Sessions, Sales and Thermal Tickets.
Row-Level Security Multi-Tenancy isolated.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.models import TenantModel
from apps.inventory.models import PharmacyProduct, ProductBatch
from apps.customers.models import CustomerAccount
from common.utils import generate_ticket_number

class CashSession(TenantModel):
    """
    Daily POS Cashier session. Tracks cash float, sales totals, and closing discrepancies.
    """
    STATUS_CHOICES = [
        ("OPEN", _("Session Ouverte")),
        ("CLOSED", _("Session Clôturée")),
    ]

    cashier = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="cash_sessions",
        verbose_name=_("Caissier / Responsable")
    )
    session_date = models.DateField(default=timezone.now, db_index=True, verbose_name=_("Date de session"))
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ouverte à"))
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Clôturée à"))
    initial_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Fonds de caisse initial (FCFA)")
    )
    expected_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Total théorique espèces attendu (FCFA)")
    )
    actual_cash_counted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Espèces réelles comptées (FCFA)")
    )
    cash_difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Écart de caisse (FCFA)")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="OPEN",
        db_index=True,
        verbose_name=_("Statut de la session")
    )
    notes = models.TextField(blank=True, default="", verbose_name=_("Observations"))

    class Meta:
        db_table = "pos_cashsession"
        verbose_name = _("Session de Caisse")
        verbose_name_plural = _("Sessions de Caisse")
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Caisse {self.cashier.username} du {self.session_date} ({self.get_status_display()})"


class Sale(TenantModel):
    """
    Completed or credit sale ticket generated at the POS counter.
    """
    PAYMENT_METHOD_CHOICES = [
        ("ESPECE", _("Espèces")),
        ("WAVE", _("Wave")),
        ("OMONEY", _("Orange Money")),
        ("COMPTE_CLIENT", _("Compte Client")),
        ("MIXTE", _("Paiement Mixte")),
        ("CARTE_BANCAIRE", _("Carte Bancaire")),
        ("CHEQUE", _("Chèque")),
    ]

    STATUS_CHOICES = [
        ("PAID", _("Payé")),
        ("CREDIT", _("Vente à crédit")),
        ("CANCELLED", _("Ticket Annulé")),
    ]

    cash_session = models.ForeignKey(
        CashSession,
        on_delete=models.CASCADE,
        related_name="sales",
        verbose_name=_("Session de Caisse")
    )
    cashier = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sales",
        verbose_name=_("Caissier")
    )
    ticket_number = models.CharField(
        max_length=64,
        db_index=True,
        default=generate_ticket_number,
        verbose_name=_("Numéro de Ticket")
    )
    customer = models.ForeignKey(
        CustomerAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        verbose_name=_("Compte Client")
    )
    total_ht = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Total HT"))
    total_tva = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name=_("Total TVA"))
    total_ttc = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Total TTC à payer (FCFA)"))
    payment_method = models.CharField(
        max_length=32,
        choices=PAYMENT_METHOD_CHOICES,
        default="ESPECE",
        verbose_name=_("Mode de paiement")
    )
    amount_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Montant reçu")
    )
    change_returned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Monnaie rendue")
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PAID",
        db_index=True,
        verbose_name=_("Statut du ticket")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "pos_sale"
        verbose_name = _("Vente / Ticket de Caisse")
        verbose_name_plural = _("Ventes / Tickets de Caisse")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "ticket_number"],
                name="unique_tenant_sale_ticket"
            )
        ]

    def clean(self):
        super().clean()
        if self.cash_session_id and self.cash_session.tenant_id != self.tenant_id:
            raise ValidationError(_("La session de caisse doit appartenir à la même officine."))
        if self.customer_id and self.customer.tenant_id != self.tenant_id:
            raise ValidationError(_("Le compte client doit appartenir à la même officine."))

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.total_ttc} FCFA ({self.get_payment_method_display()})"


class SaleItem(TenantModel):
    """
    Individual medication item line on a sale ticket with FEFO batch assignment.
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Vente liée")
    )
    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.CASCADE,
        related_name="sale_items",
        verbose_name=_("Produit")
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_items",
        verbose_name=_("Lot décrémenté (FEFO)")
    )
    quantity = models.PositiveIntegerField(verbose_name=_("Quantité vendue"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Prix unitaire (FCFA)"))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Total ligne (FCFA)"))

    class Meta:
        db_table = "pos_saleitem"
        verbose_name = _("Ligne de Vente")
        verbose_name_plural = _("Lignes de Vente")
        ordering = ["id"]

    def clean(self):
        super().clean()
        if self.sale_id and self.sale.tenant_id != self.tenant_id:
            raise ValidationError(_("La vente doit appartenir à la même officine."))
        if self.product_id and self.product.tenant_id != self.tenant_id:
            raise ValidationError(_("Le produit doit appartenir à la même officine."))
        if self.batch_id and self.batch.tenant_id != self.tenant_id:
            raise ValidationError(_("Le lot doit appartenir à la même officine."))

    def __str__(self):
        return f"{self.product.name} x {self.quantity} = {self.total_price} FCFA"
