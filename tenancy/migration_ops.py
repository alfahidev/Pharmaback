"""
Reusable Migration Operations for PostgreSQL Row-Level Security Policies.
Strictly implements Rule 4, 5, 8, and 15 of PostgreSQL RLS Multi-Tenancy.
Source: https://docs.djangoproject.com/en/6.0/topics/migrations/#special-operations
"""
from django.db import migrations

def create_rls_policy(table_name: str, tenant_id_col: str = "tenant_id") -> migrations.RunSQL:
    """
    Generates a RunSQL migration operation that:
    1. Enables and FORCES RLS on the table (Rule 4 & 8).
    2. Drops existing policy if present.
    3. Creates a policy enforcing USING (SELECT/DELETE/UPDATE) and WITH CHECK (INSERT/UPDATE) (Rule 5).
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
