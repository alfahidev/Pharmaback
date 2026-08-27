"""
PostgreSQL Row-Level Security (RLS) Policies Migration for Customer Models.
Enforces Rule 4, 5, 8, and 15 of PostgreSQL Multi-Tenancy.
"""
from django.db import migrations
from tenancy.migration_ops import create_rls_policy

class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0002_initial"),
    ]

    operations = [
        create_rls_policy(table_name="customers_customeraccount"),
        create_rls_policy(table_name="customers_customertransaction"),
    ]
