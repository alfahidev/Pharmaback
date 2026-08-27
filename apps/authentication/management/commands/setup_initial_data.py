"""
Management command to seed initial platform data (Plan Unique, SaaS Owner, Sample Catalog).
Usage:
    python manage.py setup_initial_data
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tenancy.models import SubscriptionPlan
from apps.catalog.models import MedicamentCatalog

User = get_user_model()

class Command(BaseCommand):
    help = "Initialise le Plan Unique PRO, le compte Propriétaire SaaS et un catalogue national de base"

    def handle(self, *args, **options):
        # 1. Create Default Plan
        plan, p_created = SubscriptionPlan.objects.get_or_create(
            code="standard_pro",
            defaults={
                "name": "PLAN UNIQUE PRO",
                "price": Decimal("30000.00"),
                "duration_days": 30,
                "description": "Plan complet tout-en-un pour officine: POS, Stocks FEFO, Crédits & Comptabilité.",
                "is_active": True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f" Plan {'créé' if p_created else 'existant'} : {plan.name}"))

        # 2. Create SaaS Owner
        owner, o_created = User.objects.get_or_create(
            username="saas_admin",
            defaults={
                "email": "admin@saas.sn",
                "role": "SAAS_OWNER",
                "phone": "770000000",
                "is_superuser": True,
                "is_staff": True,
                "pharmacy": None,
            }
        )
        if o_created:
            owner.set_password("SaasOwner2026!")
            owner.save()
            self.stdout.write(self.style.SUCCESS(" Propriétaire SaaS créé : saas_admin / SaasOwner2026!"))
        else:
            self.stdout.write(self.style.SUCCESS(" Propriétaire SaaS déjà existant : saas_admin"))

        # 3. Seed Sample National Catalog
        sample_meds = [
            {"barcode": "3400930000010", "name": "Doliprane 1000mg Comprimés", "dci": "Paracétamol", "form_dosage": "Boîte de 8 comprimés", "default_category": "ANTALGIQUE"},
            {"barcode": "3400930000020", "name": "Augmentin 1g/125mg Adulte", "dci": "Amoxicilline + Acide Clavulanique", "form_dosage": "Boîte de 14 sachets", "default_category": "ANTIBIOTIQUE"},
            {"barcode": "3400930000030", "name": "Efferalgan 1g Comprimés Effervescents", "dci": "Paracétamol", "form_dosage": "Tube de 8 comprimés", "default_category": "ANTALGIQUE"},
            {"barcode": "3400930000040", "name": "Spasfon Lyoc 80mg", "dci": "Phloroglucinol", "form_dosage": "Boîte de 10 lyophilisats", "default_category": "ANTISPASMODIQUE"},
            {"barcode": "3400930000050", "name": "Cétirizine 10mg Comprimés", "dci": "Cétirizine", "form_dosage": "Boîte de 30 comprimés", "default_category": "ANTIHISTAMINIQUE"},
            {"barcode": "3400930000060", "name": "Artemether + Lumefantrine 20/120mg", "dci": "Artemether + Lumefantrine", "form_dosage": "Boîte de 24 comprimés", "default_category": "ANTIPALUDIQUE"},
        ]

        count = 0
        for item in sample_meds:
            _, created = MedicamentCatalog.objects.get_or_create(
                barcode=item["barcode"],
                defaults=item
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f" Catalogue National : {count} médicaments ajoutés."))
