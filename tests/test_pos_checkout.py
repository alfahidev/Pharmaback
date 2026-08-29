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

    def test_checkout_blocked_without_open_session(self):
        """Checkout fails with error if cashier does not have an open cash session."""
        response = self.client.post("/api/pharmacy/pos/checkout/", {
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payment_method": "ESPECE",
            "amount_received": "2000.00",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Aucune session de caisse ouverte", str(response.data))

    def test_session_open_rejected_if_already_open(self):
        """Cannot open a second cash session if an existing session is currently OPEN."""
        # 1. First open succeeds
        resp1 = self.client.post("/api/pharmacy/pos/session/open/", {"initial_cash": "15000.00"}, format="json")
        self.assertEqual(resp1.status_code, 201)

        # 2. Second open is rejected with HTTP 400
        resp2 = self.client.post("/api/pharmacy/pos/session/open/", {"initial_cash": "20000.00"}, format="json")
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.data["code"], "SESSION_ALREADY_OPEN")

    def test_top_products_and_sales_filtering(self):
        """Tests top 10 most sold products endpoint and filtering sales by cashier_username."""
        with tenant_context(self.pharmacy.id):
            # Open cash session
            self.client.post("/api/pharmacy/pos/session/open/", {"initial_cash": "10000.00"}, format="json")

            # Perform a sale of 3 units of Spasfon
            self.client.post("/api/pharmacy/pos/checkout/", {
                "items": [{"product_id": self.product.id, "quantity": 3}],
                "payment_method": "ESPECE",
                "amount_received": "6000.00",
            }, format="json")

            # 1. Check top products endpoint
            top_resp = self.client.get("/api/pharmacy/pos/top-products/")
            self.assertEqual(top_resp.status_code, 200)
            self.assertTrue(len(top_resp.data) >= 1)
            top_item = top_resp.data[0]
            self.assertEqual(top_item["name"], "Spasfon Lyoc 80mg")
            self.assertEqual(top_item["total_units_sold"], 3)

            # 2. Check sales filtering by cashier_username
            sales_resp = self.client.get("/api/pharmacy/pos/sales/?cashier_username=caissiere_awa")
            self.assertEqual(sales_resp.status_code, 200)
            self.assertEqual(len(sales_resp.data["results"]), 1)
            self.assertEqual(sales_resp.data["results"][0]["cashier_username"], "caissiere_awa")

            # Non-existent cashier returns empty
            empty_resp = self.client.get("/api/pharmacy/pos/sales/?cashier_username=inconnu")
            self.assertEqual(empty_resp.status_code, 200)
            self.assertEqual(len(empty_resp.data["results"]), 0)

    def test_split_payment_espece_and_wave(self):
        """Test multi-payment (e.g. Total 17,000 FCFA -> ESPECE: 10,000 + WAVE: 7,000)."""
        with tenant_context(self.pharmacy.id):
            # Create a 17,000 FCFA product
            costly_product = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400939999999",
                name="Tensiomètre Électronique",
                purchase_price_ht=Decimal("12000.00"),
                selling_price=Decimal("17000.00"),
            )
            ProductBatch.objects.create(
                tenant=self.pharmacy,
                product=costly_product,
                batch_number="LOT-TENSIO",
                expiration_date=date.today() + timedelta(days=365),
                quantity_received=10,
                quantity_current=10,
            )

            # Open session with 20,000 FCFA
            session_resp = self.client.post("/api/pharmacy/pos/session/open/", {
                "initial_cash": "20000.00"
            }, format="json")
            session_id = session_resp.data["id"]

            # Perform Split Payment: 10,000 ESPECE + 7,000 WAVE
            checkout_payload = {
                "items": [
                    {"product_id": costly_product.id, "quantity": 1}
                ],
                "payment_method": "MIXTE",
                "payments": [
                    {"method": "ESPECE", "amount": "10000.00"},
                    {"method": "WAVE", "amount": "7000.00"}
                ],
                "amount_received": "10000.00"
            }

            response = self.client.post("/api/pharmacy/pos/checkout/", checkout_payload, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Decimal(str(response.data["total_ttc"])), Decimal("17000.00"))
            self.assertEqual(response.data["payment_method"], "MIXTE")
            self.assertEqual(len(response.data["payment_details"]), 2)
            self.assertEqual(response.data["payment_details"][0], {"method": "ESPECE", "amount": "10000.00"})
            self.assertEqual(response.data["payment_details"][1], {"method": "WAVE", "amount": "7000.00"})

            # Cash session expected cash should only increase by the 10,000 FCFA cash portion!
            session = CashSession.objects.get(id=session_id)
            self.assertEqual(session.expected_cash, Decimal("30000.00")) # 20000 + 10000


