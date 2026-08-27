"""
Tests for POS Caisse, High-Speed Scan, Cash Sessions, Atomic Checkout, FEFO Lot Decrement, and Customer Credits.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.context import tenant_context
from apps.authentication.models import User
from apps.inventory.models import PharmacyProduct, ProductBatch, StockMovement
from apps.customers.models import CustomerAccount, CustomerTransaction
from apps.pos.models import CashSession, Sale, SaleItem

class POSCheckoutTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(name="PLAN UNIQUE PRO", code="standard_pro")
        self.pharmacy = Tenant.objects.create(name="Pharmacie Fann", code="pharma_fann")
        TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )

        self.cashier = User.objects.create_user(
            username="caissiere_awa",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="CAISSIER",
        )
        self.client.force_authenticate(user=self.cashier)

        with tenant_context(self.pharmacy.id):
            # Product with 2 batches (FEFO: Lot 1 expires earlier than Lot 2)
            self.product = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000050",
                alternate_barcode="CIP50",
                name="Spasfon Lyoc 80mg",
                purchase_price_ht=Decimal("1200.00"),
                selling_price=Decimal("1800.00"),
                reorder_threshold=10,
            )

            # Batch 1 (Expires in 30 days) - 5 units
            self.batch_1 = ProductBatch.objects.create(
                tenant=self.pharmacy,
                product=self.product,
                batch_number="LOT-EARLY",
                expiration_date=date.today() + timedelta(days=30),
                quantity_received=5,
                quantity_current=5,
            )
            # Batch 2 (Expires in 180 days) - 20 units
            self.batch_2 = ProductBatch.objects.create(
                tenant=self.pharmacy,
                product=self.product,
                batch_number="LOT-LATER",
                expiration_date=date.today() + timedelta(days=180),
                quantity_received=20,
                quantity_current=20,
            )

            # Customer Account
            self.customer = CustomerAccount.objects.create(
                tenant=self.pharmacy,
                name="Mamadou Ndiaye",
                phone="771234567",
                account_type="PREPAID",
                current_balance=Decimal("10000.00"),
                credit_limit=Decimal("5000.00"),
            )

    def test_pos_fast_scan(self):
        """POS Scan endpoint returns product and batch indicators in milliseconds."""
        with tenant_context(self.pharmacy.id):
            response = self.client.get("/api/pharmacy/pos/scan/?barcode=3400930000050")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["name"], "Spasfon Lyoc 80mg")
            self.assertEqual(Decimal(str(response.data["selling_price"])), Decimal("1800.00"))
            self.assertEqual(response.data["total_stock"], 25)
            self.assertTrue(response.data["is_expiring_soon"])

    def test_cash_session_lifecycle(self):
        """Opening and closing cash session with discrepancy calculation."""
        with tenant_context(self.pharmacy.id):
            # Open session
            open_resp = self.client.post("/api/pharmacy/pos/session/open/", {
                "initial_cash": "20000.00",
                "notes": "Fonds de caisse du matin",
            }, format="json")
            self.assertEqual(open_resp.status_code, 201)
            session_id = open_resp.data["id"]
            self.assertEqual(open_resp.data["status"], "OPEN")
            self.assertEqual(Decimal(str(open_resp.data["expected_cash"])), Decimal("20000.00"))

            # Close session with cash count
            close_resp = self.client.post("/api/pharmacy/pos/session/close/", {
                "actual_cash_counted": "19500.00",
                "notes": "Manquant 500F",
            }, format="json")
            self.assertEqual(close_resp.status_code, 200)
            self.assertEqual(close_resp.data["status"], "CLOSED")
            self.assertEqual(Decimal(str(close_resp.data["cash_difference"])), Decimal("-500.00"))

    def test_atomic_checkout_fefo_decrement(self):
        """Checkout 8 units: decrements 5 from earlier Batch 1, and 3 from Batch 2."""
        with tenant_context(self.pharmacy.id):
            # Open cash session
            self.client.post("/api/pharmacy/pos/session/open/", {"initial_cash": "10000.00"}, format="json")

            checkout_payload = {
                "items": [
                    {"product_id": self.product.id, "quantity": 8}
                ],
                "payment_method": "ESPECE",
                "amount_received": "15000.00",
            }
            response = self.client.post("/api/pharmacy/pos/checkout/", checkout_payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Decimal(str(response.data["total_ttc"])), Decimal("14400.00")) # 8 * 1800
            self.assertEqual(Decimal(str(response.data["change_returned"])), Decimal("600.00")) # 15000 - 14400

            # Verify FEFO Batch quantities
            self.batch_1.refresh_from_db()
            self.batch_2.refresh_from_db()
            self.assertEqual(self.batch_1.quantity_current, 0) # 5 - 5 = 0
            self.assertEqual(self.batch_2.quantity_current, 17) # 20 - 3 = 17

            # Verify Sale Items created
            self.assertEqual(SaleItem.objects.filter(product=self.product).count(), 2)

            # Verify Stock Movements
            movements = StockMovement.objects.filter(product=self.product, movement_type="OUT_SALE")
            self.assertEqual(movements.count(), 2)

    def test_customer_account_checkout_and_credit_limit(self):
        """Buying with COMPTE_CLIENT debits balance in real time and checks limit."""
        with tenant_context(self.pharmacy.id):
            self.client.post("/api/pharmacy/pos/session/open/", {"initial_cash": "0.00"}, format="json")

            # Buy 2 Spasfon = 3600 FCFA
            response = self.client.post("/api/pharmacy/pos/checkout/", {
                "items": [{"product_id": self.product.id, "quantity": 2}],
                "payment_method": "COMPTE_CLIENT",
                "customer_id": self.customer.id,
            }, format="json")
            self.assertEqual(response.status_code, 201)

            self.customer.refresh_from_db()
            self.assertEqual(self.customer.current_balance, Decimal("6400.00")) # 10000 - 3600

            # Customer ledger entry
            trans = CustomerTransaction.objects.filter(customer=self.customer, transaction_type="PURCHASE").first()
            self.assertIsNotNone(trans)
            self.assertEqual(trans.amount, Decimal("3600.00"))
            self.assertEqual(trans.balance_after, Decimal("6400.00"))
