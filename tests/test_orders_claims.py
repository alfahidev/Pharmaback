"""
Tests for Wholesaler Suppliers, Automated Replenishment Orders, Delivery CSV Reception, and Claims.
"""
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
from apps.suppliers.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierClaim

class SuppliersAndOrdersTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(name="PLAN UNIQUE PRO", code="standard_pro")
        self.pharmacy = Tenant.objects.create(name="Pharmacie Medina", code="pharma_medina")
        TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )
        self.pharmacist = User.objects.create_user(
            username="pharma_fall",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="PHARMACIEN",
        )
        self.client.force_authenticate(user=self.pharmacist)

        with tenant_context(self.pharmacy.id):
            self.supplier = Supplier.objects.create(
                tenant=self.pharmacy,
                name="Laborex Sénégal",
                phone="338390000",
                contact_person="M. Diallo",
            )
            # Low stock product
            self.product = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000060",
                name="Cétirizine 10mg",
                purchase_price_ht=Decimal("1500.00"),
                selling_price=Decimal("2200.00"),
                reorder_threshold=20, # Stock is 0 -> Low stock
            )

    def test_generate_order_from_sales(self):
        """Auto-generates draft purchase order proposition for products below critical threshold."""
        with tenant_context(self.pharmacy.id):
            response = self.client.post(
                "/api/pharmacy/suppliers/orders/generate-from-sales/?period=week",
                {"supplier_id": self.supplier.id},
                format="json"
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data["supplier_name"], "Laborex Sénégal")
            self.assertEqual(response.data["status"], "DRAFT")
            self.assertEqual(len(response.data["items"]), 1)
            self.assertEqual(response.data["items"][0]["product"], self.product.id)

    def test_import_delivery_csv(self):
        """Imports delivery note CSV, creates product batches, movements, and marks order RECEIVED."""
        with tenant_context(self.pharmacy.id):
            order = PurchaseOrder.objects.create(
                tenant=self.pharmacy,
                supplier=self.supplier,
                status="DRAFT",
            )
            PurchaseOrderItem.objects.create(
                tenant=self.pharmacy,
                order=order,
                product=self.product,
                quantity_ordered=40,
                unit_purchase_price=Decimal("1500.00"),
            )

            # Delivery CSV content
            csv_content = (
                "Code-barre;Désignation;Lot;Péremption;Quantité reçue;Prix Achat\n"
                "3400930000060;Cétirizine 10mg;LOT-LAB-001;30/11/2027;40;1500,00\n"
            )
            file_obj = SimpleUploadedFile("bon_livraison_laborex.csv", csv_content.encode("utf-8"), content_type="text/csv")

            response = self.client.post(
                f"/api/pharmacy/suppliers/orders/{order.id}/import-delivery-csv/",
                {"file": file_obj},
                format="multipart"
            )
            self.assertEqual(response.status_code, 200)

            order.refresh_from_db()
            self.assertEqual(order.status, "RECEIVED")

            # Check inventory batch created
            self.product.refresh_from_db()
            self.assertEqual(self.product.total_stock, 40)
            batch = ProductBatch.objects.get(product=self.product, batch_number="LOT-LAB-001")
            self.assertEqual(batch.quantity_current, 40)

    def test_supplier_claim_creation(self):
        """Pharmacist files a dispute claim for damaged goods."""
        with tenant_context(self.pharmacy.id):
            response = self.client.post("/api/pharmacy/suppliers/claims/", {
                "supplier": self.supplier.id,
                "claim_type": "DAMAGED",
                "product_name": "Cétirizine 10mg",
                "batch_number": "LOT-LAB-001",
                "quantity_affected": 5,
                "description": "5 boites écrasées et non commercialisables lors du déchargement.",
            }, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data["status"], "PENDING")
            self.assertEqual(response.data["claim_type"], "DAMAGED")
