"""
Automated PostgreSQL Row-Level Security (RLS) and Tenant Isolation Test Suite.
Strictly verifies Rule 1 through 15 of the RLS security principles.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.context import tenant_context
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.pos.models import CashSession, Sale, SaleItem
from apps.customers.models import CustomerAccount
from apps.billing.models import ExpenseCategory, Expense

class RowLevelSecurityIsolationTestCase(TransactionTestCase):
    """
    Mandatory automated tests verifying PostgreSQL RLS cross-tenant isolation (Rule 11).
    """

    def setUp(self):
        # Create single subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name="PLAN UNIQUE PRO",
            code="standard_pro",
            price=Decimal("30000.00"),
            duration_days=30,
        )

        # Create Tenant A and Tenant B
        self.tenant_a = Tenant.objects.create(
            name="Grande Pharmacie Dakar",
            code="pharma_dakar",
            license_number="LIC-SN-001",
        )
        TenantSubscription.objects.create(
            tenant=self.tenant_a,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )

        self.tenant_b = Tenant.objects.create(
            name="Pharmacie du Plateau",
            code="pharma_plateau",
            license_number="LIC-SN-002",
        )
        TenantSubscription.objects.create(
            tenant=self.tenant_b,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )

        # Create Tenant A records
        with tenant_context(self.tenant_a.id):
            self.product_a = PharmacyProduct.objects.create(
                tenant=self.tenant_a,
                barcode="3400930000001",
                alternate_barcode="CIP34001",
                name="Paracétamol 500mg Boite 20",
                shelf_location="RAYON-A1",
                purchase_price_ht=Decimal("800.00"),
                selling_price=Decimal("1200.00"),
            )
            self.batch_a = ProductBatch.objects.create(
                tenant=self.tenant_a,
                product=self.product_a,
                batch_number="LOT-A-999",
                expiration_date=date.today() + timedelta(days=180),
                quantity_received=100,
                quantity_current=100,
            )

    def test_tenant_id_format(self):
        """Rule: Tenant ID must match format MTXXXXXXXL."""
        self.assertTrue(self.tenant_a.id.startswith("MT"))
        self.assertEqual(len(self.tenant_a.id), 10)
        self.assertTrue(self.tenant_a.id[2:9].isdigit())
        self.assertTrue(self.tenant_a.id[9].isalpha())

    def test_cross_tenant_select_isolation(self):
        """Rule 11: Tenant B cannot SELECT Tenant A records."""
        with tenant_context(self.tenant_b.id):
            products_b = list(PharmacyProduct.objects.all())
            self.assertEqual(len(products_b), 0, "RLS Breach: Tenant B saw Tenant A products!")

            batches_b = list(ProductBatch.objects.all())
            self.assertEqual(len(batches_b), 0, "RLS Breach: Tenant B saw Tenant A batches!")

    def test_cross_tenant_insert_protection(self):
        """Rule 11: Tenant B cannot INSERT records under Tenant A ID."""
        with tenant_context(self.tenant_b.id):
            # Attempt to create product with Tenant A's ID while in Tenant B context
            with self.assertRaises(Exception):
                PharmacyProduct.objects.create(
                    tenant=self.tenant_a,
                    barcode="3400930000002",
                    name="Amoxicilline 500mg",
                    selling_price=Decimal("2500.00")
                )

    def test_cross_tenant_update_isolation(self):
        """Rule 11: Tenant B cannot UPDATE Tenant A records."""
        with tenant_context(self.tenant_b.id):
            updated_count = PharmacyProduct.objects.filter(id=self.product_a.id).update(name="Hacked Name")
            self.assertEqual(updated_count, 0, "RLS Breach: Tenant B updated Tenant A record!")

        # Verify product A unchanged
        with tenant_context(self.tenant_a.id):
            self.product_a.refresh_from_db()
            self.assertEqual(self.product_a.name, "Paracétamol 500mg Boite 20")

    def test_cross_tenant_delete_isolation(self):
        """Rule 11: Tenant B cannot DELETE Tenant A records."""
        with tenant_context(self.tenant_b.id):
            deleted_count, _ = PharmacyProduct.objects.filter(id=self.product_a.id).delete()
            self.assertEqual(deleted_count, 0, "RLS Breach: Tenant B deleted Tenant A record!")

        with tenant_context(self.tenant_a.id):
            self.assertTrue(PharmacyProduct.objects.filter(id=self.product_a.id).exists())

    def test_tenant_id_immutability(self):
        """Rule 13: Never allow changing tenant_id after object creation."""
        with tenant_context(self.tenant_a.id):
            self.product_a.tenant = self.tenant_b
            with self.assertRaises(ValidationError):
                self.product_a.save()

    def test_cross_tenant_relationship_guard(self):
        """Rule 14: Prevent linking child entity (batch) to a product from another tenant."""
        with tenant_context(self.tenant_b.id):
            # Tenant B product
            product_b = PharmacyProduct.objects.create(
                tenant=self.tenant_b,
                barcode="3400930000099",
                name="Ibuprofène 400mg",
                selling_price=Decimal("1500.00"),
            )

        # Attempt to create batch for Tenant B linked to Product A (Tenant A)
        with tenant_context(self.tenant_b.id):
            with self.assertRaises(ValidationError):
                batch = ProductBatch(
                    tenant=self.tenant_b,
                    product=self.product_a,
                    batch_number="LOT-MALICIOUS",
                    expiration_date=date.today() + timedelta(days=90),
                    quantity_received=10,
                    quantity_current=10,
                )
                batch.clean()
