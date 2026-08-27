"""
Tests for Pharmacy Stock, CSV Import/Export, and FEFO Expiry Calculations.
"""
import io
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.context import tenant_context
from apps.authentication.models import User
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement

class InventoryCSVTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(name="PLAN UNIQUE PRO", code="standard_pro")
        self.pharmacy = Tenant.objects.create(name="Pharmacie Almadies", code="pharma_almadies")
        TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )
        self.pharmacist = User.objects.create_user(
            username="pharmacien_ali",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="PHARMACIEN",
        )
        self.client.force_authenticate(user=self.pharmacist)

    def test_import_standard_csv(self):
        """Imports CSV with exact standard format and populates products, batches, and movements."""
        csv_data = (
            "Code 1;Code 2;Code géo;Label;Quantité;Prix unitaire d'achat HT;Prix unitaire de vente;Date de péremption la plus proche\n"
            "3400930000010;CIP10;RAY-A1;Doliprane 1000mg;50;1000,00;1500,00;31/12/2026\n"
            "3400930000020;CIP20;RAY-B2;Augmentin 1g;25;3500,00;5000,00;15/06/2027\n"
        )
        file_obj = SimpleUploadedFile("export-stocks-2026.csv", csv_data.encode("utf-8"), content_type="text/csv")

        with tenant_context(self.pharmacy.id):
            response = self.client.post(
                "/api/pharmacy/inventory/import-csv/",
                {"file": file_obj},
                format="multipart"
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["created_products"], 2)

            doliprane = PharmacyProduct.objects.get(barcode="3400930000010")
            self.assertEqual(doliprane.name, "Doliprane 1000mg")
            self.assertEqual(doliprane.selling_price, Decimal("1500.00"))
            self.assertEqual(doliprane.total_stock, 50)
            self.assertEqual(doliprane.batches.count(), 1)
            self.assertEqual(StockMovement.objects.filter(product=doliprane).count(), 1)

    def test_export_standard_csv(self):
        """Exports CSV matching the standard template."""
        with tenant_context(self.pharmacy.id):
            p = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000030",
                alternate_barcode="CIP30",
                name="Efferalgan 1g",
                shelf_location="RAY-E3",
                purchase_price_ht=Decimal("900.00"),
                selling_price=Decimal("1400.00"),
            )
            ProductBatch.objects.create(
                tenant=self.pharmacy,
                product=p,
                batch_number="LOT-EFF-01",
                expiration_date=date(2027, 1, 1),
                quantity_received=30,
                quantity_current=30,
            )

            response = self.client.get("/api/pharmacy/inventory/export-csv/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
            content = response.content.decode("utf-8")
            self.assertIn("Code 1;Code 2;Code géo;Label;Quantité", content)
            self.assertIn("3400930000030", content)
            self.assertIn("Efferalgan 1g", content)

    def test_fefo_expiry_indicators(self):
        """Calculates is_expiring_soon and months_until_expiry properly."""
        today = date.today()
        with tenant_context(self.pharmacy.id):
            p = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000040",
                name="Sirop Toux 150ml",
                selling_price=Decimal("2200.00"),
                reorder_threshold=15,
            )
            # Batch expiring in 40 days (< 90 days)
            ProductBatch.objects.create(
                tenant=self.pharmacy,
                product=p,
                batch_number="LOT-SOON",
                expiration_date=today + timedelta(days=40),
                quantity_received=10,
                quantity_current=10,
            )

            self.assertTrue(p.is_expiring_soon)
            self.assertEqual(p.months_until_expiry, 1)
            self.assertTrue(p.is_low_stock) # 10 <= 15

    def test_quick_restock_by_barcode_and_alternate(self):
        """Quickly restocks a product using either barcode or alternate barcode."""
        with tenant_context(self.pharmacy.id):
            p = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000050",
                alternate_barcode="CIP50",
                name="Vitamine C 1000mg",
                selling_price=Decimal("2000.00"),
                purchase_price_ht=Decimal("1200.00"),
            )
            # Initial stock is 0
            self.assertEqual(p.total_stock, 0)

        # 1. Restock via primary barcode (+20 units)
        response1 = self.client.post("/api/pharmacy/inventory/products/quick-restock/", {
            "barcode": "3400930000050",
            "quantity": 20,
            "batch_number": "LOT-VITC-01",
            "expiration_date": "2027-12-31",
        }, format="json")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.data["total_stock"], 20)

        # 2. Restock via alternate barcode (+15 units)
        response2 = self.client.post("/api/pharmacy/inventory/products/quick-restock/", {
            "barcode": "CIP50",
            "quantity": 15,
        }, format="json")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.data["total_stock"], 35)

        # Verify stock movements created
        with tenant_context(self.pharmacy.id):
            p.refresh_from_db()
            self.assertEqual(p.total_stock, 35)
            self.assertEqual(StockMovement.objects.filter(product=p).count(), 2)

