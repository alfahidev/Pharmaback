"""
Django management command to create a SaaS Platform Owner / Superadmin account.
Usage:
    python manage.py createsaasowner --username admin --email admin@saas.com --password SecretPassword123!
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tenancy.models import SubscriptionPlan

User = get_user_model()

class Command(BaseCommand):
    help = "Création du compte Propriétaire de la Plateforme SaaS (SAAS_OWNER)"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="saas_admin", help="Nom d'utilisateur")
        parser.add_argument("--email", type=str, default="admin@saas.com", help="Email de l'administrateur")
        parser.add_argument("--password", type=str, default="SaasOwner2026!", help="Mot de passe")
        parser.add_argument("--phone", type=str, default="770000000", help="Téléphone")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]
        phone = options["phone"]

        # Ensure default plan exists
        SubscriptionPlan.objects.get_or_create(
            code="standard_pro",
            defaults={
                "name": "PLAN UNIQUE PRO",
                "price": 30000.00,
                "duration_days": 30,
                "description": "Plan complet tout-en-un: POS, Stocks FEFO, Crédits, Fournisseurs et Comptabilité.",
            }
        )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": "SAAS_OWNER",
                "phone": phone,
                "is_superuser": True,
                "is_staff": True,
                "pharmacy": None,  # SaaS Owner does not belong to any specific pharmacy tenant
            }
        )

        user.set_password(password)
        user.role = "SAAS_OWNER"
        user.is_superuser = True
        user.is_staff = True
        user.pharmacy = None
        user.save()

        action_str = "créé" if created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(
            f" Compte Propriétaire SaaS {action_str} avec succès !\n"
            f"   - Username : {username}\n"
            f"   - Email    : {email}\n"
            f"   - Rôle     : SAAS_OWNER\n"
            f"   - Officine : Aucune (Global SuperAdmin)"
        ))
