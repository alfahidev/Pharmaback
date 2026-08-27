"""
Tests for SaaS Owner Subscription Management, Authentication, and Custom JWT Claims.
"""
from datetime import timedelta
from django.utils import timezone
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from tenancy.models import Tenant, SubscriptionPlan, TenantSubscription
from tenancy.context import tenant_context
from apps.authentication.models import User

class AuthAndSaasSubscriptionTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(
            name="PLAN UNIQUE PRO",
            code="standard_pro",
            price=30000.00,
            duration_days=30,
        )

        # SaaS Platform Owner
        self.saas_owner = User.objects.create_superuser(
            username="saas_admin",
            email="admin@saas.com",
            password="StrongPassword123!",
            role="SAAS_OWNER",
        )

        # Create Tenant
        self.pharmacy = Tenant.objects.create(
            name="Pharmacie Principale",
            code="pharma_principale",
            license_number="LIC-12345",
            city="Dakar",
        )
        self.subscription = TenantSubscription.objects.create(
            tenant=self.pharmacy,
            plan=self.plan,
            status="ACTIVE",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
        )

        # Pharmacy Staff Users
        self.titulaire = User.objects.create_user(
            username="dr_diop",
            email="diop@pharma.com",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="ADMIN",
        )
        self.cashier = User.objects.create_user(
            username="caissier_fatou",
            email="fatou@pharma.com",
            password="StrongPassword123!",
            pharmacy=self.pharmacy,
            role="CAISSIER",
        )

    def test_saas_owner_creates_tenant_with_subscription(self):
        """SaaS Owner registers a new pharmacy with owner info and gets default subscription attached."""
        self.client.force_authenticate(user=self.saas_owner)
        response = self.client.post("/api/saas/tenants/", {
            "name": "Pharmacie Mermoz",
            "code": "pharma_mermoz",
            "license_number": "LIC-9988",
            "city": "Dakar",
            "initial_duration_days": 30,
            "initial_status": "ACTIVE",
            "owner": {
                "username": "dr_mermoz",
                "email": "mermoz@pharma.sn",
                "first_name": "Ibrahima",
                "last_name": "Sarr",
                "auto_generate_password": True,
            }
        }, format="json")
        self.assertEqual(response.status_code, 201)
        tenant_id = response.data["id"]
        self.assertTrue(tenant_id.startswith("MT"))

        # Verify owner user was created with role ADMIN
        self.assertIn("owner", response.data)
        self.assertEqual(response.data["owner"]["username"], "dr_mermoz")
        self.assertEqual(response.data["owner"]["role"], "ADMIN")
        self.assertTrue(response.data["owner"]["generated_password"].startswith("Pharma@"))

        # Verify user exists in database
        owner_user = User.objects.get(username="dr_mermoz")
        self.assertEqual(owner_user.pharmacy.id, tenant_id)
        self.assertEqual(owner_user.role, "ADMIN")

        # Verify subscription was created
        new_tenant = Tenant.objects.get(id=tenant_id)
        self.assertIsNotNone(new_tenant.subscription)
        self.assertEqual(new_tenant.subscription.status, "ACTIVE")
        self.assertTrue(new_tenant.subscription.is_currently_valid())

    def test_saas_owner_creates_owner_on_existing_tenant(self):
        """SaaS Owner adds a titular admin to an existing pharmacy via /create-owner/."""
        self.client.force_authenticate(user=self.saas_owner)
        response = self.client.post(
            f"/api/saas/tenants/{self.pharmacy.id}/create-owner/",
            {
                "username": "nouveau_titulaire",
                "email": "nouveau@pharma.sn",
                "first_name": "Ousmane",
                "last_name": "Ba",
                "auto_generate_password": True,
            },
            format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["owner"]["username"], "nouveau_titulaire")
        self.assertEqual(response.data["owner"]["role"], "ADMIN")
        self.assertEqual(response.data["owner"]["pharmacy_id"], str(self.pharmacy.id))

    def test_saas_owner_extends_subscription(self):
        """SaaS Owner extends an existing subscription by 60 days."""
        self.client.force_authenticate(user=self.saas_owner)
        initial_end = self.subscription.end_date
        response = self.client.post(
            f"/api/saas/tenants/{self.pharmacy.id}/extend-subscription/",
            {"days": 60},
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.end_date > initial_end + timedelta(days=58))

    def test_jwt_login_claims(self):
        """JWT login returns token with custom tenant and role claims."""
        response = self.client.post("/api/auth/login/", {
            "username": "dr_diop",
            "password": "StrongPassword123!",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["role"], "ADMIN")
        self.assertEqual(response.data["user"]["pharmacy"]["id"], str(self.pharmacy.id))

    def test_subscription_expiration_middleware(self):
        """If pharmacy subscription expires, requests are blocked with HTTP 403."""
        # Expire subscription
        self.subscription.status = "EXPIRED"
        self.subscription.end_date = timezone.now() - timedelta(days=1)
        self.subscription.save()

        # Try accessing pharmacy inventory as cashier
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get("/api/pharmacy/inventory/products/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("code"), "SUBSCRIPTION_REQUIRED")

        # But subscription status check is still accessible
        status_resp = self.client.get("/api/pharmacy/subscription/status/")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["status"], "EXPIRED")
