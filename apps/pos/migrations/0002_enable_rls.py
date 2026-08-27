"""
PostgreSQL Row-Level Security (RLS) Policies Migration for POS Models.
Enforces Rule 4, 5, 8, and 15 of PostgreSQL Multi-Tenancy.
"""
from django.db import migrations
from tenancy.migration_ops import create_rls_policy

class Migration(migrations.Migration):
    dependencies = [
        ("pos", "0001_initial"),
    ]

    operations = [
        create_rls_policy(table_name="pos_cashsession"),
        create_rls_policy(table_name="pos_sale"),
        create_rls_policy(table_name="pos_saleitem"),
    ]
