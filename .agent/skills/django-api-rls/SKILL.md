---
name: django-api-rls
description: |
  Django 6.0+ & DRF production best practices for Row-Level Multi-Tenancy and Single-Tenant APIs.
  Specialized for PostgreSQL Row-Level Security (RLS), tenant context isolation, Composite Primary Keys,
  Tasks framework, SimpleJWT authentication, Redis caching, CSP, and high-security test suites.
---

# Django 6.0+ API — Production Skill (Row-Level Security / RLS)

This skill captures all conventions, patterns, and best practices for building production-grade multi-tenant APIs using **Django 6.0+**, **Django REST Framework (DRF)**, and **PostgreSQL Row-Level Security (RLS)** as the definitive security boundary, grounded directly in the official Django documentation and PostgreSQL security standards.

---

## ⚠️ Source Policy — Read This First

> **Strict rule: Use only code and patterns that are documented in the official Django 6.0 documentation.**
> If a pattern you need is not explicitly detailed in this SKILL, you MUST fetch the official Django docs at `https://docs.djangoproject.com/en/6.0/` and cite it before writing code.
> No guessing. No outdated blog posts. Official docs only.
> Don't create tenant_id with 1,2,3 ,that's easy to guess and but unique in a format (MTXXXXXXXL) where X is a random integer and L is a letter.

```
NEED PATTERN ──→ CHECK SKILL ──→ FOUND? USE IT  ──→ CITE SECTION / URL
                      │
                      ▼ NOT FOUND
     FETCH OFFICIAL DOCS (https://docs.djangoproject.com/en/6.0/)
                      │
                      ▼
            VERIFY ──→ ADD TO SKILL ──→ CITE URL
```

---

## 🛡️ The 15 Core Principles of PostgreSQL Row-Level Security (RLS) Multi-Tenancy

Every multi-tenant model, endpoint, migration, and test MUST strictly comply with these 15 rules:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                      THE 15 MANDATORY RLS SECURITY RULES                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1.  Never trust tenant_id from the client.                                                       │
│ 2.  Tenant context must come from authenticated server-side identity.                            │
│ 3.  Every tenant-owned table must have an explicit tenant_id.                                    │
│ 4.  PostgreSQL RLS is the final tenant-isolation boundary.                                       │
│ 5.  Every RLS policy must consider both USING and WITH CHECK where applicable.                   │
│ 6.  Never use a persistent SET for tenant context with pooled connections.                       │
│ 7.  Tenant context must be transaction-scoped (SET LOCAL app.current_tenant_id = ...).            │
│ 8.  Application DB role must not have BYPASSRLS (must be a non-superuser role).                  │
│ 9.  Never rely only on Django queryset filtering for tenant isolation (Defense-in-depth).        │
│ 10. Never expose cross-tenant queries through normal application endpoints.                      │
│ 11. Test SELECT, INSERT, UPDATE, and DELETE cross-tenant isolation.                              │
│ 12. Test Celery / background jobs, admin, imports, and management commands.                      │
│ 13. Never allow changing tenant_id after object creation unless explicitly authorized.           │
│ 14. Add database constraints to prevent cross-tenant relationships where necessary.              │
│ 15. Any new tenant-owned model requires an RLS policy migration and security tests.              │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Stack Detection — Do This Before Writing Any Code

Always inspect `requirements.txt`, `pyproject.toml`, or `Pipfile` first to verify library versions:

```
STACK DETECTED:
- Django==6.0.x (or 5.2+ upgrading to 6.0)
- djangorestframework
- djangorestframework-simplejwt
- psycopg (psycopg 3) or psycopg2-binary
- PostgreSQL 16+ (with native Row-Level Security enabled)
- django-redis / redis
- django-cors-headers
- drf-spectacular
```

---

## Official Documentation Index (`https://docs.djangoproject.com/en/6.0/`)

| Category              | Section / Topic                | Official Documentation Deep Link                                        |
| :-------------------- | :----------------------------- | :---------------------------------------------------------------------- |
| **Getting Started**   | Install & First App            | https://docs.djangoproject.com/en/6.0/intro/tutorial01/                 |
| **Models & DB**       | Models & Fields                | https://docs.djangoproject.com/en/6.0/topics/db/models/                 |
| **Models & DB**       | Making Queries                 | https://docs.djangoproject.com/en/6.0/topics/db/queries/                |
| **Models & DB**       | Composite Primary Keys         | https://docs.djangoproject.com/en/6.0/topics/db/composite-primary-keys/ |
| **Models & DB**       | Aggregation & Search           | https://docs.djangoproject.com/en/6.0/topics/db/aggregation/            |
| **Models & DB**       | Transactions & Raw SQL         | https://docs.djangoproject.com/en/6.0/topics/db/transactions/           |
| **HTTP Requests**     | URL Dispatcher & Views         | https://docs.djangoproject.com/en/6.0/topics/http/urls/                 |
| **HTTP Requests**     | Middleware & Sessions          | https://docs.djangoproject.com/en/6.0/topics/http/middleware/           |
| **Class-Based Views** | Built-in & Async CBVs          | https://docs.djangoproject.com/en/6.0/topics/class-based-views/         |
| **Forms**             | Form Handling & Validation     | https://docs.djangoproject.com/en/6.0/topics/forms/                     |
| **Templates**         | Engine & Custom Tags           | https://docs.djangoproject.com/en/6.0/topics/templates/                 |
| **Migrations**        | Operations & RunSQL            | https://docs.djangoproject.com/en/6.0/topics/migrations/                |
| **File Handling**     | Files & Storage API (STORAGES) | https://docs.djangoproject.com/en/6.0/topics/files/                     |
| **Testing**           | Testing Tools & Transactions   | https://docs.djangoproject.com/en/6.0/topics/testing/                   |
| **Authentication**    | User Auth & Permissions        | https://docs.djangoproject.com/en/6.0/topics/auth/                      |
| **Caching**           | Low-Level & Redis Cache        | https://docs.djangoproject.com/en/6.0/topics/cache/                     |
| **Tasks**             | Tasks Framework (New in 6.0)   | https://docs.djangoproject.com/en/6.0/topics/tasks/                     |
| **Security**          | Security in Django & Headers   | https://docs.djangoproject.com/en/6.0/topics/security/                  |
| **Performance**       | Database & Query Optimization  | https://docs.djangoproject.com/en/6.0/topics/performance/               |
| **Settings**          | Core Settings & Topical Index  | https://docs.djangoproject.com/en/6.0/ref/settings/                     |
| **Signals**           | Model & Request Signals        | https://docs.djangoproject.com/en/6.0/topics/signals/                   |
| **System Check**      | System Check Framework         | https://docs.djangoproject.com/en/6.0/topics/checks/                    |

---

## Project Architecture & Directory Layout (Row-Level Multi-Tenancy)

In a Row-Level Multi-Tenant architecture, all tenants share a unified database and schema, with strict data isolation enforced at the PostgreSQL engine level via RLS and transaction-scoped session variables (`app.current_tenant_id`).

```
pharmaback/
├── manage.py
├── core/
│   ├── settings/
│   │   ├── __init__.py       # Environment-based switcher
│   │   ├── base.py           # Shared apps, REST_FRAMEWORK, STORAGES, CACHES
│   │   ├── production.py     # Swarm secrets, SSL, CSP, RLS DB credentials
│   │   └── development.py    # Local debug settings
│   ├── urls.py               # Root URLconf
│   ├── wsgi.py
│   └── asgi.py
├── tenancy/                  # Core Tenancy & RLS Module
│   ├── models.py             # Tenant (Pharmacy), TenantModel abstract base class
│   ├── middleware.py         # Transactional RLS Context Middleware (SET LOCAL)
│   ├── context.py            # Thread-safe / async context manager for tenant isolation
│   ├── managers.py           # TenantAwareQuerySet & TenantManager
│   └── migration_ops.py      # Reusable Migration Operations for Postgres RLS Policies
├── apps/
│   ├── authentication/       # Custom User model, SimpleJWT with tenant claims, blocklist
│   ├── catalog/              # Global shared medication database (Public/Global Catalog)
│   ├── inventory/            # Tenant-owned stock, batches (FEFO), expiry tracking
│   ├── pos/                  # Point of Sale, cash sessions, barcode scanning, sales
│   ├── customers/            # Customer credit accounts, prepayments, balance tracking
│   ├── suppliers/            # Suppliers, purchase orders, delivery imports, claims
│   └── billing/              # Expenses, payment breakdown, financial statements
└── tests/
    ├── conftest.py
    └── test_rls_security.py  # 15-Rule verification test suite
```

---

## Core Multi-Tenancy & PostgreSQL RLS Implementation

### 1. Abstract `TenantModel` & Immutability Guard (Rules 3, 13, 14)

```python
# tenancy/models.py
# Source: https://docs.djangoproject.com/en/6.0/topics/db/models/
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tenancy.managers import TenantManager

class Tenant(models.Model):
    """Represents a tenant organization (e.g., Pharmacy / Clinic)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Tenant Name"))
    code = models.SlugField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenants"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class TenantModel(models.Model):
    """
    Abstract base class for all tenant-owned models.
    Enforces explicit tenant_id, tenant-aware manager, and tenant_id immutability.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
        editable=False,
    )

    objects = TenantManager()
    all_objects = models.Manager()  # For administrative/system audits only

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        # Rule 13: Prevent changing tenant_id after creation
        if self.pk:
            original_tenant_id = type(self).all_objects.filter(pk=self.pk).values_list("tenant_id", flat=True).first()
            if original_tenant_id and original_tenant_id != self.tenant_id:
                raise ValidationError(_("Tenant ID cannot be modified once set."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

---

### 2. Transaction-Scoped Tenant Context Middleware (Rules 1, 2, 6, 7, 8)

```python
# tenancy/middleware.py
# Source: https://docs.djangoproject.com/en/6.0/topics/http/middleware/
# Source: https://docs.djangoproject.com/en/6.0/topics/db/transactions/
from django.db import connection, transaction
from django.http import JsonResponse
from tenancy.context import set_current_tenant_id, reset_current_tenant_id

class TransactionalTenantRLSMiddleware:
    """
    Middleware establishing PostgreSQL Row-Level Security context for each HTTP request.

    Security Guarantees:
    - Never trusts tenant_id from client headers or body (Rule 1).
    - Extracts tenant identity strictly from authenticated JWT/user (Rule 2).
    - Uses transaction-scoped 'SET LOCAL' preventing connection-pool leakage (Rules 6 & 7).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        tenant_id = None

        if user and user.is_authenticated and hasattr(user, "tenant_id") and user.tenant_id:
            tenant_id = str(user.tenant_id)

        # Set Python thread/async context
        token = set_current_tenant_id(tenant_id)

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    if tenant_id:
                        # Rule 7: SET LOCAL is strictly scoped to current transaction block
                        cursor.execute("SET LOCAL app.current_tenant_id = %s;", [tenant_id])
                    else:
                        cursor.execute("SET LOCAL app.current_tenant_id = '';")

                response = self.get_response(request)
                return response
        finally:
            reset_current_tenant_id(token)
```

---

### 3. Thread-Safe & Async Context Manager for Background Tasks & Celery (Rule 12)

```python
# tenancy/context.py
import contextvars
from contextlib import contextmanager
from django.db import connection, transaction

_current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)

def get_current_tenant_id():
    return _current_tenant_id.get()

def set_current_tenant_id(tenant_id):
    return _current_tenant_id.set(tenant_id)

def reset_current_tenant_id(token):
    _current_tenant_id.reset(token)

@contextmanager
def tenant_context(tenant_or_id):
    """
    Context manager for background tasks, CLI commands, and test suites to set RLS context.
    Usage:
        with tenant_context(pharmacy.id):
            Product.objects.all()  # Isolated to this pharmacy
    """
    tenant_id = str(getattr(tenant_or_id, "id", tenant_or_id))
    token = set_current_tenant_id(tenant_id)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = %s;", [tenant_id])
            yield
    finally:
        reset_current_tenant_id(token)
```

---

### 4. Database Migrations for PostgreSQL RLS Policies (Rules 4, 5, 8, 15)

Create reusable migration helpers to enable RLS and generate strictly checked `USING` and `WITH CHECK` policies:

```python
# tenancy/migration_ops.py
# Source: https://docs.djangoproject.com/en/6.0/topics/migrations/#special-operations
from django.db import migrations

def create_rls_policy(table_name: str, tenant_id_col: str = "tenant_id") -> migrations.RunSQL:
    """
    Generates a RunSQL migration operation that:
    1. Enables and FORCES RLS on the table (even for table owners).
    2. Drops existing policy if present.
    3. Creates a policy enforcing USING (SELECT/DELETE/UPDATE) and WITH CHECK (INSERT/UPDATE).
    """
    policy_name = f"{table_name}_tenant_isolation_policy"

    forward_sql = f"""
    ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY;
    ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS "{policy_name}" ON "{table_name}";

    CREATE POLICY "{policy_name}" ON "{table_name}"
    AS PERMISSIVE
    FOR ALL
    TO PUBLIC
    USING (
        "{tenant_id_col}"::text = NULLIF(current_setting('app.current_tenant_id', true), '')
    )
    WITH CHECK (
        "{tenant_id_col}"::text = NULLIF(current_setting('app.current_tenant_id', true), '')
    );
    """

    reverse_sql = f"""
    DROP POLICY IF EXISTS "{policy_name}" ON "{table_name}";
    ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY;
    """

    return migrations.RunSQL(forward_sql, reverse_sql)
```

#### Example Model Migration File:

```python
# apps/inventory/migrations/0002_enable_rls.py
from django.db import migrations
from tenancy.migration_ops import create_rls_policy

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        create_rls_policy(table_name="inventory_pharmacyproduct"),
        create_rls_policy(table_name="inventory_productbatch"),
        create_rls_policy(table_name="inventory_stockmovement"),
    ]
```

---

### 5. Secure DRF ViewSet & Serializer Integration (Rules 1, 2, 9, 10)

```python
# common/viewsets.py
from rest_framework import viewsets, permissions, serializers
from rest_framework.exceptions import PermissionDenied

class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet enforcing dual-layer tenant isolation:
    - Layer 1: Queryset auto-filtering (Django ORM).
    - Layer 2: Automatic tenant_id injection on write operations.
    - Layer 3: PostgreSQL Row-Level Security at the database driver level.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated or not getattr(user, "tenant_id", None):
            return self.queryset.none()
        # Rule 9: Queryset filtering paired with RLS defense-in-depth
        return super().get_queryset().filter(tenant_id=user.tenant_id)

    def perform_create(self, serializer):
        # Rules 1 & 2: Explicit server-side injection of tenant identity
        user = self.request.user
        if not getattr(user, "tenant_id", None):
            raise PermissionDenied("User does not belong to any active tenant.")
        serializer.save(tenant=user.tenant)
```

---

### 6. Cross-Tenant Relationship Guard (Rule 14)

To prevent referencing a foreign key from another tenant (e.g. assigning Pharmacy A's sale item to Pharmacy B's product), use **Composite Unique Constraints** and enforce validation:

```python
# apps/inventory/models.py
from django.db import models
from tenancy.models import TenantModel

class PharmacyProduct(TenantModel):
    barcode = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "inventory_pharmacyproduct"
        constraints = [
            # Rule 14: Ensure barcode is unique PER TENANT
            models.UniqueConstraint(
                fields=["tenant", "barcode"],
                name="unique_tenant_product_barcode"
            )
        ]

class ProductBatch(TenantModel):
    product = models.ForeignKey(PharmacyProduct, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=64)
    expiration_date = models.DateField(db_index=True)
    quantity = models.IntegerField(default=0)

    class Meta:
        db_table = "inventory_productbatch"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "batch_number"],
                name="unique_tenant_product_batch"
            )
        ]

    def clean(self):
        super().clean()
        # Rule 14: Ensure linked product belongs to the exact same tenant
        if self.product_id and self.product.tenant_id != self.tenant_id:
            raise ValidationError("Product must belong to the same tenant as the batch.")
```

---

## 🔒 Comprehensive RLS Cross-Tenant Security Test Suite (Rule 11)

Every project must maintain an automated test suite verifying that cross-tenant operations are strictly rejected at the database level:

```python
# tests/test_rls_security.py
from decimal import Decimal
from django.test import TransactionTestCase
from django.db import connection, IntegrityError
from tenancy.models import Tenant
from tenancy.context import tenant_context
from apps.inventory.models import PharmacyProduct

class RowLevelSecurityIsolationTestCase(TransactionTestCase):
    """
    Mandatory automated tests verifying PostgreSQL RLS cross-tenant isolation (Rule 11).
    """

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Pharmacie A", code="pharma_a")
        self.tenant_b = Tenant.objects.create(name="Pharmacie B", code="pharma_b")

        # Create Product for Tenant A
        with tenant_context(self.tenant_a.id):
            self.product_a = PharmacyProduct.objects.create(
                tenant=self.tenant_a,
                barcode="3400930000001",
                name="Paracétamol 500mg",
                selling_price=Decimal("1500.00")
            )

    def test_cross_tenant_select_isolation(self):
        """Rule 11: Tenant B cannot SELECT Tenant A records."""
        with tenant_context(self.tenant_b.id):
            products_b = list(PharmacyProduct.objects.all())
            self.assertEqual(len(products_b), 0, "RLS Breach: Tenant B saw Tenant A products!")

    def test_cross_tenant_insert_protection(self):
        """Rule 11: Tenant B cannot INSERT records under Tenant A ID."""
        with tenant_context(self.tenant_b.id):
            with self.assertRaises(Exception):
                # RLS WITH CHECK policy must reject this write
                PharmacyProduct.objects.create(
                    tenant=self.tenant_a,
                    barcode="3400930000002",
                    name="Amoxicilline 500mg",
                    selling_price=Decimal("2500.00")
                )

    def test_cross_tenant_update_isolation(self):
        """Rule 11: Tenant B cannot UPDATE Tenant A records."""
        with tenant_context(self.tenant_b.id):
            # Raw SQL update or ORM update should affect 0 rows
            updated_count = PharmacyProduct.objects.filter(id=self.product_a.id).update(name="Hacked Name")
            self.assertEqual(updated_count, 0, "RLS Breach: Tenant B updated Tenant A record!")

        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.name, "Paracétamol 500mg")

    def test_cross_tenant_delete_isolation(self):
        """Rule 11: Tenant B cannot DELETE Tenant A records."""
        with tenant_context(self.tenant_b.id):
            deleted_count, _ = PharmacyProduct.objects.filter(id=self.product_a.id).delete()
            self.assertEqual(deleted_count, 0, "RLS Breach: Tenant B deleted Tenant A record!")

        with tenant_context(self.tenant_a.id):
            self.assertTrue(PharmacyProduct.objects.filter(id=self.product_a.id).exists())
```

---

## Django 6.0 Core Settings & Storage Patterns

### 1. Storage Configuration (`STORAGES`)

```python
# core/settings/base.py
# Source: https://docs.djangoproject.com/en/6.0/ref/settings/#storages
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage"
                   if STORAGE_BACKEND in ["s3", "r2"]
                   else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

---

### 2. Redis Caching & Token Blocklist

```python
# core/settings/base.py
# Source: https://docs.djangoproject.com/en/6.0/topics/cache/
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "KEY_PREFIX": "pharma_cache",
        }
    }
}
```

---

### 3. Production Security Headers & CSP

```python
# core/settings/production.py
# Source: https://docs.djangoproject.com/en/6.0/topics/security/
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
```

---

## Conflict Protocol

When documented Django 6.0 patterns or PostgreSQL RLS requirements conflict with incoming code changes, log and resolve the conflict immediately:

```
CONFLICT DETECTED:
Incoming code relies on client-provided 'tenant_id' in API serializers or query parameters.
Violation of Rule 1: Never trust tenant_id from the client.

Resolution:
Remove 'tenant_id' from serializer input fields and inject 'tenant=request.user.tenant'
server-side within 'perform_create' and transaction-scoped RLS middleware.
```
