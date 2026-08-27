"""
Customer Accounts, Prepaid Balances, and Credit Transactions.
Row-Level Security Multi-Tenancy isolated.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.models import TenantModel

class CustomerAccount(TenantModel):
    """
    Customer account for tracking deposits (acompte) and monthly credit lines.
    """
    ACCOUNT_TYPE_CHOICES = [
        ("PREPAID", _("Compte Prépayé (Acompte)")),
        ("CREDIT_MONTHLY", _("Client Conventionné (Facture Fin de Mois)")),
    ]

    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Nom complet / Entreprise"))
    phone = models.CharField(max_length=64, blank=True, default="", db_index=True, verbose_name=_("Téléphone"))
    account_type = models.CharField(
        max_length=32,
        choices=ACCOUNT_TYPE_CHOICES,
        default="PREPAID",
        verbose_name=_("Type de compte")
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Solde actuel (Positif=Acompte, Négatif=Dette)")
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Plafond de crédit autorisé (FCFA)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Compte actif"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers_customeraccount"
        verbose_name = _("Compte Client")
        verbose_name_plural = _("Comptes Clients")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone"],
                name="unique_tenant_customer_phone",
                condition=~models.Q(phone="")
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.phone}) - Solde: {self.current_balance} FCFA"

    def can_charge(self, amount: Decimal) -> tuple[bool, str]:
        """
        Determines if the account has enough credit/balance to process a purchase.
        """
        available = self.current_balance + self.credit_limit
        if amount > available:
            return False, f"Plafond de crédit dépassé. Disponible: {available} FCFA, Demandé: {amount} FCFA."
        return True, "Solde suffisant."


class CustomerTransaction(TenantModel):
    """
    Ledger of customer deposits, purchases, repayments, and refunds.
    """
    TRANSACTION_TYPE_CHOICES = [
        ("DEPOSIT", _("Dépôt / Recharge Acompte")),
        ("PURCHASE", _("Achat au comptoir (Débit)")),
        ("REFUND", _("Remboursement / Avoir")),
        ("PAYMENT_CREDIT", _("Règlement de facture impayée")),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("ESPECE", _("Espèces")),
        ("WAVE", _("Wave")),
        ("OMONEY", _("Orange Money")),
        ("COMPTE_CLIENT", _("Compte Client")),
        ("CHEQUE", _("Chèque")),
        ("VIREMENT", _("Virement bancaire")),
        ("AUTRE", _("Autre")),
    ]

    customer = models.ForeignKey(
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Compte Client")
    )
    sale = models.ForeignKey(
        "pos.Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_transactions",
        verbose_name=_("Vente liée")
    )
    transaction_type = models.CharField(
        max_length=32,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name=_("Type d'opération")
    )
    payment_method = models.CharField(
        max_length=32,
        choices=PAYMENT_METHOD_CHOICES,
        default="ESPECE",
        verbose_name=_("Mode de règlement")
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant"))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Solde après opération"))
    note = models.TextField(blank=True, default="", verbose_name=_("Commentaire / Motif"))
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Enregistré par")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "customers_customertransaction"
        verbose_name = _("Transaction Compte Client")
        verbose_name_plural = _("Transactions Comptes Clients")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.customer_id and self.customer.tenant_id != self.tenant_id:
            raise ValidationError(_("Le client doit appartenir à la même officine."))

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.customer.name}: {self.amount} FCFA"
