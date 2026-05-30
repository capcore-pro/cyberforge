"""
Nettoyage Supabase — supprime les données fictives/de test.

Usage (depuis backend/) :
    python scripts/cleanup_supabase_test_data.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from typing import Any

import httpx

# Permet l'import config depuis backend/
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from config import get_settings, plain_secret_str  # noqa: E402

# Tables à vider intégralement (si présentes)
TRUNCATE_TABLES = frozenset(
    {
        "transactions",
        "devis",
        "factures",
        "notifications",
    }
)

# Colonnes texte à inspecter pour détecter des données fictives
TEXT_COLUMNS = frozenset(
    {
        "nom",
        "name",
        "title",
        "titre",
        "description",
        "summary",
        "prompt",
        "prompt_original",
        "prompt_last",
        "email",
        "entreprise",
        "company",
        "notes",
        "message",
        "body",
        "content",
        "slug",
        "token",
        "number",
        "telephone",
        "phone",
    }
)

# Motifs fictifs (insensible à la casse)
FAKE_PATTERNS = [
    r"\btest\b",
    r"\bdemo\b",
    r"\bdémo\b",
    r"\bfictif\b",
    r"\bexemple\b",
    r"\bdupont\b",
    r"\bmartin\b",
    r"\bjean\b",
    r"boulangerie le fournil",
    r"\bfournil\b",
    r"\blorem\b",
    r"\bplaceholder\b",
    r"\bfake\b",
    r"\bsample\b",
    r"\bfixture\b",
    r"\bmock\b",
    r"example\.com",
    r"test@",
    r"@test\.",
    r"nova studio",
    r"acme\b",
    r"cyberforge test",
]
_FAKE_RE = re.compile("|".join(FAKE_PATTERNS), re.IGNORECASE)


def _headers(key: str, *, prefer: str | None = None) -> dict[str, str]:
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _is_fake_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return bool(_FAKE_RE.search(text))


def _row_is_fake(row: dict[str, Any]) -> bool:
    for key, val in row.items():
        if key in TEXT_COLUMNS or key.endswith("_text") or key.endswith("_label"):
            if _is_fake_value(val):
                return True
        if isinstance(val, str) and len(val) < 500 and _is_fake_value(val):
            return True
    return False


def _pk_column(row: dict[str, Any]) -> str:
    if "id" in row:
        return "id"
    for key in row:
        if key.endswith("_id") and isinstance(row[key], (str, int)):
            return key
    return "id"


async def fetch_openapi_tables(client: httpx.AsyncClient, rest_base: str, key: str) -> list[str]:
    """Liste les tables exposées par PostgREST."""
    try:
        resp = await client.get(
            rest_base,
            headers={**_headers(key), "Accept": "application/openapi+json"},
        )
        if resp.status_code >= 400:
            return []
        spec = resp.json()
        paths = spec.get("paths") or {}
        tables: list[str] = []
        for path in paths:
            if path.startswith("/") and path.count("/") == 1:
                name = path.strip("/")
                if name and not name.startswith("rpc/"):
                    tables.append(name)
        return sorted(set(tables))
    except Exception:
        return []


async def count_rows(
    client: httpx.AsyncClient,
    rest_base: str,
    key: str,
    table: str,
) -> int | None:
    url = f"{rest_base}/{table}"
    for select_col in ("id", "*"):
        resp = await client.head(
            url,
            headers={**_headers(key), "Prefer": "count=exact"},
            params={"select": select_col},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            continue
        cr = resp.headers.get("content-range") or ""
        if "/" in cr:
            try:
                return int(cr.split("/")[-1])
            except ValueError:
                pass
        return 0
    return None


async def fetch_all_rows(
    client: httpx.AsyncClient,
    rest_base: str,
    key: str,
    table: str,
    *,
    page_size: int = 1000,
) -> list[dict[str, Any]] | None:
    url = f"{rest_base}/{table}"
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        resp = await client.get(
            url,
            headers=_headers(key),
            params={"select": "*", "limit": page_size, "offset": offset},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise RuntimeError(f"GET {table} HTTP {resp.status_code}: {resp.text[:300]}")
        batch = resp.json()
        if not isinstance(batch, list):
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


async def delete_by_ids(
    client: httpx.AsyncClient,
    rest_base: str,
    key: str,
    table: str,
    ids: list[str],
    *,
    pk: str = "id",
) -> int:
    if not ids:
        return 0
    url = f"{rest_base}/{table}"
    deleted = 0
    chunk = 80
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        in_list = ",".join(part)
        resp = await client.delete(
            url,
            headers=_headers(key),
            params={pk: f"in.({in_list})"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"DELETE {table} HTTP {resp.status_code}: {resp.text[:300]}"
            )
        deleted += len(part)
    return deleted


async def truncate_table(
    client: httpx.AsyncClient,
    rest_base: str,
    key: str,
    table: str,
) -> int:
    rows = await fetch_all_rows(client, rest_base, key, table)
    if rows is None:
        return 0
    if not rows:
        return 0
    pk = _pk_column(rows[0])
    ids = [str(r[pk]) for r in rows if pk in r and r[pk] is not None]
    return await delete_by_ids(client, rest_base, key, table, ids, pk=pk)


async def main() -> None:
    settings = get_settings()
    url = (settings.supabase_url or "").strip().rstrip("/")
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        print("ERREUR: SUPABASE_URL et SUPABASE_SECRET_KEY requis dans backend/.env")
        sys.exit(1)

    rest_base = f"{url}/rest/v1"
    summary: dict[str, Any] = {
        "tables_found": [],
        "truncated": {},
        "fake_deleted": {},
        "skipped": [],
        "errors": [],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        tables = await fetch_openapi_tables(client, rest_base, key)
        if not tables:
            # Repli : tables connues dans le codebase
            tables = sorted(
                {
                    "projects",
                    "generations",
                    "demos",
                    "clients",
                    "notifications",
                    "transactions",
                    "devis",
                    "factures",
                    "managed_projects",
                    "managed_project_runs",
                    "managed_project_auth",
                    "ecommerce_products",
                    "ecommerce_orders",
                    "ecommerce_order_items",
                    "reservation_services",
                    "reservation_availability",
                    "reservation_blocks",
                    "reservations",
                }
            )

        summary["tables_found"] = tables
        print(f"Tables Supabase ({len(tables)}): {', '.join(tables)}\n")

        # Ordre : enfants avant parents (FK)
        delete_order = [
            "ecommerce_order_items",
            "ecommerce_orders",
            "generations",
            "demos",
            "managed_project_runs",
            "managed_project_auth",
            "reservations",
            "reservation_blocks",
            "reservation_availability",
            "reservation_services",
            "ecommerce_products",
            "line_items",
            "documents",
            "projects",
            "clients",
            "managed_projects",
            "transactions",
            "devis",
            "factures",
            "notifications",
        ]
        ordered = [t for t in delete_order if t in tables]
        ordered += [t for t in tables if t not in ordered]

        for table in ordered:
            try:
                if table in TRUNCATE_TABLES:
                    n = await truncate_table(client, rest_base, key, table)
                    if n:
                        summary["truncated"][table] = n
                        print(f"  [VIDÉ] {table}: {n} ligne(s) supprimée(s)")
                    elif table in tables:
                        summary["truncated"].setdefault(table, 0)
                    continue

                count_before = await count_rows(client, rest_base, key, table)
                if count_before is None and table not in tables:
                    summary["skipped"].append(f"{table} (absente)")
                    continue

                rows = await fetch_all_rows(client, rest_base, key, table)
                if rows is None:
                    summary["skipped"].append(f"{table} (inaccessible)")
                    continue
                if not rows:
                    continue

                pk = _pk_column(rows[0])
                fake_ids = [
                    str(r[pk])
                    for r in rows
                    if pk in r and r[pk] is not None and _row_is_fake(r)
                ]
                if fake_ids:
                    n = await delete_by_ids(
                        client, rest_base, key, table, fake_ids, pk=pk
                    )
                    summary["fake_deleted"][table] = n
                    print(f"  [FAKE] {table}: {n} ligne(s) fictive(s) supprimée(s)")
            except Exception as exc:
                msg = f"{table}: {exc}"
                summary["errors"].append(msg)
                print(f"  [ERREUR] {msg}")

    print("\n=== RÉSUMÉ ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    total_trunc = sum(summary["truncated"].values())
    total_fake = sum(summary["fake_deleted"].values())
    print(
        f"\nTotal: {total_trunc} lignes vidées (tables cibles) + "
        f"{total_fake} lignes fictives supprimées."
    )

    report_path = __import__("pathlib").Path(__file__).resolve().parent / "_cleanup_report.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rapport: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
