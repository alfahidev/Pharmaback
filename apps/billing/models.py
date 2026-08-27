"""
Operational Expenses, Categories, and Accounting Ledgers.
Row-Level Security Multi-Tenancy isolated.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.models import TenantModel

class ExpenseCategory(TenantModel):
    """
    Categorization of operational expenses (Rent, Electricity, Salaries, Supplies...).
    """
    name = models.CharField(max_length=128, db_index=True, verbose_name=_("Nom de la catégorie"))
    description = models.TextField(blank=True, default="", verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_expensecategory"
        verbose_name = _("Catégorie de Dépense")
        verbose_name_plural = _("Catégories de Dépenses")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_tenant_expense_category"
            )
        ]

    def __str__(self):
        return self.name


class Expense(TenantModel):
    """
    Operational cash/bank disbursement with receipt document.
    """
    PAYMENT_METHOD_CHOICES = [
        ("ESPECE", _("Espèces")),
        ("WAVE", _("Wave")),
        ("OMONEY", _("Orange Money")),
        ("CHEQUE", _("Chèque")),
        ("VIREMENT", _("Virement bancaire")),
        ("AUTRE", _("Autre")),
    ]

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name=_("Catégorie de dépense")
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant (FCFA)"))
    payment_method = models.CharField(
        max_length=32,
        choices=PAYMENT_METHOD_CHOICES,
        default="ESPECE",
        verbose_name=_("Mode de paiement")
    )
    description = models.TextField(blank=True, default="", verbose_name=_("Description / Motif de la dépense"))
    receipt_file = models.FileField(
        upload_to="expense_receipts/",
        null=True,
        blank=True,
        verbose_name=_("Pièce justificative / Reçu")
    )
    date = models.DateField(default=timezone.now, db_index=True, verbose_name=_("Date de la dépense"))
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Enregistré par")
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_expense"
        verbose_name = _("Dépense d'Exploitation")
        verbose_name_plural = _("Dépenses d'Exploitation")
        ordering = ["-date", "-created_at"]

    def clean(self):
        super().clean()
        if self.category_id and self.category.tenant_id != self.tenant_id:
            raise ValidationError(_("La catégorie doit appartenir à la même officine."))

    def __str__(self):
        return f"{self.category.name} - {self.amount} FCFA ({self.date})"
