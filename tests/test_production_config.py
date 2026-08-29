"""
Tests for Production Readiness, Healthcheck, CORS, and Swagger toggles.
"""
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from core.settings import base, production

class HealthCheckTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        """Health check returns 200 OK and valid JSON payload for container healthcheck."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "pharmaback-api")
        self.assertEqual(data["database"], "healthy")

class ProductionSettingsTestCase(SimpleTestCase):
    def test_cors_and_csrf_contains_frontend_domain(self):
        """CORS and CSRF origins properly include https://pharmacy.melakhtelecom.com."""
        self.assertIn("https://pharmacy.melakhtelecom.com", base.CORS_ALLOWED_ORIGINS)
        self.assertIn("https://pharmacy.melakhtelecom.com", base.CSRF_TRUSTED_ORIGINS)

    def test_production_security_headers(self):
        """Production settings enforce HTTPS forward header and secure cookies."""
        self.assertEqual(production.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertTrue(production.USE_X_FORWARDED_HOST)
        self.assertTrue(production.SESSION_COOKIE_SECURE)
        self.assertTrue(production.CSRF_COOKIE_SECURE)
        self.assertTrue(production.CSRF_COOKIE_HTTPONLY)

    def test_swagger_disabled_on_production_by_default(self):
        """Swagger/OpenAPI documentation is disabled in production settings."""
        self.assertFalse(production.ENABLE_SWAGGER)
