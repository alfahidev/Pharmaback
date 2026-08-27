"""
Thread-safe and async-safe tenant context management.
Enforces Rule 6, 7, and 12 of the 15 RLS principles.
"""
import contextvars
from contextlib import contextmanager
from django.db import connection, transaction

_current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)

def get_current_tenant_id():
    """Retrieve the current active tenant ID from thread/async context."""
    return _current_tenant_id.get()

def set_current_tenant_id(tenant_id):
    """Set the active tenant ID in thread/async context and return token."""
    return _current_tenant_id.set(tenant_id)

def reset_current_tenant_id(token):
    """Reset the active tenant context using the token."""
    _current_tenant_id.reset(token)

@contextmanager
def tenant_context(tenant_or_id):
    """
    Context manager for background tasks, CLI commands, migrations, and test suites.
    Executes PostgreSQL 'SET LOCAL app.current_tenant_id' inside an atomic transaction block.
    
    Usage:
        with tenant_context(pharmacy.id):
            PharmacyProduct.objects.all()  # Strictly isolated to this pharmacy
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
