"""
PostgreSQL Row-Level Security (RLS) Policies Migration for Suppliers Models.
Enforces Rule 4, 5, 8, and 15 of PostgreSQL Multi-Tenancy.
"""
from django.db import migrations
from tenancy.migration_ops import create_rls_policy

class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0001_initial"),
    ]

    operations = [
        create_rls_policy(table_name="suppliers_supplier"),
        create_rls_policy(table_name="suppliers_purchaseorder"),
        create_rls_policy(table_name="suppliers_purchaseorderitem"),
        create_rls_policy(table_name="suppliers_supplierclaim"),
    ]
