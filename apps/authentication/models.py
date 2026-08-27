"""
Custom User Model for Multi-Tenant Pharmacy SaaS.
Supports Roles: SAAS_OWNER, ADMIN (TITULAIRE), PHARMACIEN, CAISSIER, COMPTABLE.
Source: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/#substituting-a-custom-user-model
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from tenancy.models import Tenant

class User(AbstractUser):
    """
    Custom User linked to an officine/tenant with role-based permissions.
    """
    ROLE_CHOICES = [
        ("SAAS_OWNER", _("Propriétaire Plateforme SaaS")),
        ("ADMIN", _("Titulaire / Administrateur Officine")),
        ("PHARMACIEN", _("Pharmacien")),
        ("CAISSIER", _("Caissier / Vendeur")),
        ("COMPTABLE", _("Comptable / Gestionnaire")),
    ]

    pharmacy = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("Officine")
    )
    phone = models.CharField(max_length=64, blank=True, default="", verbose_name=_("Téléphone"))
    role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        default="CAISSIER",
        verbose_name=_("Rôle dans l'Officine")
    )

    class Meta:
        db_table = "auth_users"
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        ordering = ["username"]

    def __str__(self):
        pharmacy_str = self.pharmacy.name if self.pharmacy else "SaaS Platform"
        return f"{self.username} ({self.get_role_display()}) - {pharmacy_str}"

    @property
    def tenant_id(self):
        """Helper property for RLS and Tenancy middleware."""
        return str(self.pharmacy.id) if self.pharmacy else None

    @property
    def tenant(self):
        """Helper property returning the linked pharmacy/tenant."""
        return self.pharmacy
