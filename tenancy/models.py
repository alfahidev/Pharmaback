"""
Core Tenancy and Subscription Models.
Row-Level Security multi-tenancy foundation.
Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
"""
import random
import string
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.managers import TenantManager

def generate_tenant_id() -> str:
    """
    Generate unique tenant identifier matching the skill requirement:
    Format: MTXXXXXXXL (MT + 7 random integers + 1 uppercase letter).
    Example: MT8492014K
    """
    digits = "".join(random.choices(string.digits, k=7))
    letter = random.choice(string.ascii_uppercase)
    return f"MT{digits}{letter}"


class Tenant(models.Model):
    """
    Represents an independent Pharmacy (Officine) organization / Tenant.
    """
    id = models.CharField(
        primary_key=True,
        max_length=16,
        default=generate_tenant_id,
        editable=False,
        verbose_name=_("ID Officine (Tenant ID)")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'Officine"))
    code = models.SlugField(max_length=64, unique=True, db_index=True, verbose_name=_("Code unique"))
    license_number = models.CharField(max_length=128, blank=True, default="", verbose_name=_("Numéro d'agrément / Licence"))
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name=_("Téléphone"))
    address = models.TextField(blank=True, default="", verbose_name=_("Adresse physique"))
    city = models.CharField(max_length=128, blank=True, default="Dakar", verbose_name=_("Ville"))
    logo = models.ImageField(upload_to="pharmacy_logos/", null=True, blank=True, verbose_name=_("Logo"))
    is_active = models.BooleanField(default=True, verbose_name=_("Officine active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de mise à jour"))
    auto_print = models.BooleanField(default=False, verbose_name=_("Impression automatique des reçus"))

    class Meta:
        db_table = "tenants"
        ordering = ["name"]
        verbose_name = _("Officine (Tenant)")
        verbose_name_plural = _("Officines (Tenants)")

    def __str__(self):
        return f"{self.name} ({self.id})"


class SubscriptionPlan(models.Model):
    """
    Single subscription plan managed by the SaaS owner.
    """
    name = models.CharField(max_length=100, default="PLAN UNIQUE PRO", verbose_name=_("Nom du Plan"))
    code = models.SlugField(max_length=64, unique=True, default="standard_pro", verbose_name=_("Code du Plan"))
    description = models.TextField(
        blank=True,
        default="Plan tout-en-un: POS, Stocks FEFO, Comptes Clients, Fournisseurs et États Financiers.",
        verbose_name=_("Description")
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, default=30000.00, verbose_name=_("Tarif mensuel (FCFA)"))
    duration_days = models.PositiveIntegerField(default=30, verbose_name=_("Durée par défaut (jours)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Plan disponible"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        verbose_name = _("Plan d'Abonnement")
        verbose_name_plural = _("Plans d'Abonnement")

    def __str__(self):
        return f"{self.name} - {self.price} FCFA"


class TenantSubscription(models.Model):
    """
    Subscription state for an officine/tenant, manually managed by the SaaS Owner.
    """
    STATUS_CHOICES = [
        ("TRIAL", _("Période d'essai")),
        ("ACTIVE", _("Actif")),
        ("EXPIRED", _("Expiré")),
        ("SUSPENDED", _("Suspendu")),
    ]

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name=_("Officine")
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name=_("Plan")
    )
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="TRIAL",
        verbose_name=_("Statut")
    )
    start_date = models.DateTimeField(default=timezone.now, verbose_name=_("Date de début"))
    end_date = models.DateTimeField(verbose_name=_("Date de fin / Expiration"))
    is_active = models.BooleanField(default=True, verbose_name=_("Abonnement actif"))
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes de l'administrateur SaaS"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenant_subscriptions"
        verbose_name = _("Abonnement Officine")
        verbose_name_plural = _("Abonnements Officines")

    def __str__(self):
        return f"Abonnement {self.tenant.name} - {self.get_status_display()}"

    def is_currently_valid(self) -> bool:
        """Checks if the subscription is currently active and within valid dates."""
        if not self.is_active or not self.tenant.is_active:
            return False
        if self.status not in ("ACTIVE", "TRIAL"):
            return False
        return self.end_date >= timezone.now()


class TenantModel(models.Model):
    """
    Abstract base class for all private tenant-owned models.
    Enforces Rule 3 (explicit tenant_id), Rule 9 (TenantManager), and Rule 13 (Tenant immutability).
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
        editable=False,
        verbose_name=_("Officine Propriétaire")
    )

    objects = TenantManager()
    all_objects = models.Manager()  # Strictly for global administrative audits and background migrations

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        # Rule 13: Prevent changing tenant_id after object creation
        if self.pk:
            original_tenant_id = (
                type(self).all_objects.filter(pk=self.pk)
                .values_list("tenant_id", flat=True)
                .first()
            )
            if original_tenant_id and original_tenant_id != self.tenant_id:
                raise ValidationError(_("Le changement d'officine (tenant_id) est strictement interdit."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
