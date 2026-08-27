"""
Tests for Expenses, Categories, and Consolidated Financial Statements.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.context import tenant_context
from apps.authentication.models import User
from apps.inventory.models import PharmacyProduct, ProductBatch
from apps.pos.models import CashSession, Sale, SaleItem
from apps.billing.models import ExpenseCategory, Expense

class FinancialsTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(name="PLAN UNIQUE PRO", code="standard_pro")
        self.pharmacy = Tenant.objects.create(name="Pharmacie Sacré-Cœur", code="pharma_sacre_coeur")
        TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            end_date=timezone.now() + timedelta(days=30),
        )
        self.accountant = User.objects.create_user(
            username="comptable_ibra",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="COMPTABLE",
        )
        self.client.force_authenticate(user=self.accountant)

        with tenant_context(self.pharmacy.id):
            # Product
            self.product = PharmacyProduct.objects.create(
                tenant=self.pharmacy,
                barcode="3400930000070",
                name="Vitamine C 1000mg",
                purchase_price_ht=Decimal("1000.00"),
                selling_price=Decimal("1500.00"),
            )
            # Cash Session & Sales
            self.session = CashSession.objects.create(
                tenant=self.pharmacy,
                cashier=self.accountant,
                session_date=timezone.now().date(),
                initial_cash=Decimal("50000.00"),
            )
            # Sale 1 (Espèce): 2 x 1500 = 3000 FCFA
            self.sale_1 = Sale.objects.create(
                tenant=self.pharmacy,
                cash_session=self.session,
                cashier=self.accountant,
                ticket_number="VTE-20260826-0001",
                total_ht=Decimal("3000.00"),
                total_ttc=Decimal("3000.00"),
                payment_method="ESPECE",
                status="PAID",
            )
            SaleItem.objects.create(
                tenant=self.pharmacy,
                sale=self.sale_1,
                product=self.product,
                quantity=2,
                unit_price=Decimal("1500.00"),
                total_price=Decimal("3000.00"),
            )

            # Sale 2 (Wave): 3 x 1500 = 4500 FCFA
            self.sale_2 = Sale.objects.create(
                tenant=self.pharmacy,
                cash_session=self.session,
                cashier=self.accountant,
                ticket_number="VTE-20260826-0002",
                total_ht=Decimal("4500.00"),
                total_ttc=Decimal("4500.00"),
                payment_method="WAVE",
                status="PAID",
            )
            SaleItem.objects.create(
                tenant=self.pharmacy,
                sale=self.sale_2,
                product=self.product,
                quantity=3,
                unit_price=Decimal("1500.00"),
                total_price=Decimal("4500.00"),
            )

            # Expenses
            self.cat = ExpenseCategory.objects.create(tenant=self.pharmacy, name="Électricité / Senelec")
            Expense.objects.create(
                tenant=self.pharmacy,
                category=self.cat,
                amount=Decimal("2500.00"),
                payment_method="WAVE",
                description="Facture Senelec boutique",
                date=timezone.now().date(),
            )

    def test_consolidated_financial_statement(self):
        """Calculates accurate sales, expenses, COGS, gross margin, and payment methods breakdown."""
        with tenant_context(self.pharmacy.id):
            response = self.client.get("/api/pharmacy/billing/financial-statement/?period=today")
            self.assertEqual(response.status_code, 200)

            data = response.data
            self.assertEqual(Decimal(str(data["total_ventes_ttc"])), Decimal("7500.00")) # 3000 + 4500
            self.assertEqual(Decimal(str(data["total_depenses"])), Decimal("2500.00"))
            self.assertEqual(Decimal(str(data["solde_net"])), Decimal("5000.00")) # 7500 - 2500
            self.assertEqual(Decimal(str(data["cout_achat_marchandises"])), Decimal("5000.00")) # (2 + 3) * 1000
            self.assertEqual(Decimal(str(data["marge_brute_estimee"])), Decimal("2500.00")) # 7500 - 5000
            self.assertEqual(data["total_tickets_count"], 2)

            # Breakdown checks
            self.assertEqual(Decimal(str(data["ventilation_modes_paiement"]["ESPECE"]["total"])), Decimal("3000.00"))
            self.assertEqual(Decimal(str(data["ventilation_modes_paiement"]["WAVE"]["total"])), Decimal("4500.00"))

    def test_create_expense_without_description_or_receipt(self):
        """Creating an expense does not require description or receipt file."""
        response = self.client.post("/api/pharmacy/billing/expenses/", {
            "category": self.cat.id,
            "amount": "15000.00",
            "payment_method": "ESPECE",
            "date": "2026-08-26",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["description"], "")
        self.assertIsNone(response.data["receipt_file"])

