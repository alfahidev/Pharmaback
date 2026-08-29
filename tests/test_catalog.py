"""
Tests for Global National Medicament Catalog and Population from CSV.
"""
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from apps.authentication.models import User
from apps.catalog.models import MedicamentCatalog

class CatalogTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()

        # SaaS Owner
        self.saas_owner = User.objects.create_superuser(
            username="saas_admin_cat",
            email="admin_cat@saas.com",
            password="StrongPassword123!",
            role="SAAS_OWNER",
        )

        # Pharmacy Staff
        from datetime import timedelta
        from django.utils import timezone
        self.plan = SubscriptionPlan.objects.create(name="PLAN UNIQUE PRO", code="standard_pro")
        self.pharmacy = Tenant.objects.create(name="Pharmacie Test", code="pharma_test")
        TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )
        self.pharmacist = User.objects.create_user(
            username="pharma_staff",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="PHARMACIEN",
        )

        # Seed test items in catalog
        self.item1 = MedicamentCatalog.objects.create(
            barcode="4042809000733",
            alternate_barcode="4042809000733",
            geo_code="CH",
            name="BANDE HYPAFIX ADH 10M X10",
        )
        self.item2 = MedicamentCatalog.objects.create(
            barcode="8436024611748",
            alternate_barcode="8436024612615",
            geo_code="RAYON AMPOULE",
            name="POTENCIATOR 5G AMP BUV B/20",
        )

    def test_search_national_catalog_by_various_fields(self):
        """Authenticated staff can search catalog by barcode, alternate barcode, geo_code, or name."""
        self.client.force_authenticate(user=self.pharmacist)

        # 1. Search by Code 1 (barcode)
        resp1 = self.client.get("/api/catalog/?search=4042809000733")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(len(resp1.data["results"]) if "results" in resp1.data else len(resp1.data), 1)

        # 2. Search by Code 2 (alternate_barcode)
        resp2 = self.client.get("/api/catalog/?search=8436024612615")
        self.assertEqual(resp2.status_code, 200)
        items = resp2.data["results"] if "results" in resp2.data else resp2.data
        self.assertEqual(items[0]["name"], "POTENCIATOR 5G AMP BUV B/20")

        # 3. Search by name
        resp3 = self.client.get("/api/catalog/?search=POTENCIATOR")
        self.assertEqual(resp3.status_code, 200)
        items3 = resp3.data["results"] if "results" in resp3.data else resp3.data
        self.assertEqual(items3[0]["geo_code"], "RAYON AMPOULE")

    def test_saas_owner_creates_catalog_item_with_optional_category(self):
        """SaaS Owner can add a new national reference with optional category, DCI, and form."""
        self.client.force_authenticate(user=self.saas_owner)

        payload = {
            "barcode": "3400936382237",
            "alternate_barcode": "",
            "geo_code": "RAYON AMPOULE",
            "name": "MAG 2 SS 122 mg sol oral amp 10 ml bte/30",
            # default_category, dci, form_dosage are omitted
        }
        response = self.client.post("/api/catalog/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["barcode"], "3400936382237")
        self.assertEqual(response.data["default_category"], "")
        self.assertEqual(response.data["dci"], "")

    def test_non_saas_owner_cannot_create_or_delete_catalog_item(self):
        """Pharmacy staff can read the catalog but cannot create or delete entries."""
        self.client.force_authenticate(user=self.pharmacist)

        # Try create -> 403 Forbidden
        post_resp = self.client.post("/api/catalog/", {
            "barcode": "9999999999999",
            "name": "Unauthorized Drug",
        }, format="json")
        self.assertEqual(post_resp.status_code, 403)

        # Try delete -> 403 Forbidden
        del_resp = self.client.delete(f"/api/catalog/{self.item1.id}/")
        self.assertEqual(del_resp.status_code, 403)
