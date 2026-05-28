"""
Helpers for Supabase PostgREST grants.

Supabase changes defaults on May 30, 2026: new tables in `public` require
explicit GRANT to be accessible via PostgREST / supabase-js.
"""

from __future__ import annotations


DEFAULT_ROLES = ("anon", "authenticated", "service_role")


def grant_crud_sql(table: str, *, schema: str = "public", roles: tuple[str, ...] = DEFAULT_ROLES) -> str:
    roles_sql = ", ".join(roles)
    return (
        f"grant select, insert, update, delete on table {schema}.{table} to {roles_sql};"
    )


def default_privileges_sql(*, schema: str = "public", roles: tuple[str, ...] = DEFAULT_ROLES) -> str:
    roles_sql = ", ".join(roles)
    return "\n".join(
        [
            f"alter default privileges in schema {schema} grant select, insert, update, delete on tables to {roles_sql};",
            f"alter default privileges in schema {schema} grant usage, select, update on sequences to {roles_sql};",
            f"alter default privileges in schema {schema} grant execute on functions to {roles_sql};",
        ]
    )

