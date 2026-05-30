"""
Vide intégralement les tables Supabase listées (DELETE all rows, structure conservée).

Usage: python scripts/truncate_supabase_tables.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_settings, plain_secret_str  # noqa: E402

# Tables cibles (demandées par l'utilisateur)
TARGET_TABLES = [
    "projects",
    "generations",
    "managed_projects",
    "demos",
    "ecommerce_products",
    "devis",
    "factures",
    "transactions",
]

# Dépendances à vider d'abord (FK → tables cibles)
PREREQ_TABLES = [
    "ecommerce_order_items",
    "ecommerce_orders",
    "managed_project_runs",
    "managed_project_auth",
    "reservation_blocks",
    "reservations",
]


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def count_rows(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    table: str,
) -> int | None:
    """None = table inaccessible (404)."""
    url = f"{base}/{table}"
    for sel in ("id", "*"):
        resp = await client.head(
            url,
            headers={**_headers(key), "Prefer": "count=exact"},
            params={"select": sel},
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


async def fetch_ids(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    table: str,
) -> list[str] | None:
    url = f"{base}/{table}"
    ids: list[str] = []
    offset = 0
    while True:
        resp = await client.get(
            url,
            headers=_headers(key),
            params={"select": "id", "limit": 1000, "offset": offset},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            resp2 = await client.get(
                url,
                headers=_headers(key),
                params={"select": "*", "limit": 1000, "offset": offset},
            )
            if resp2.status_code == 404:
                return None
            if resp2.status_code >= 400:
                raise RuntimeError(f"{table} GET {resp2.status_code}: {resp2.text[:200]}")
            batch = resp2.json()
        else:
            batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break
        for row in batch:
            if not isinstance(row, dict):
                continue
            pk = row.get("id")
            if pk is None:
                for k, v in row.items():
                    if k.endswith("_id") or k == "id":
                        pk = v
                        break
            if pk is not None:
                ids.append(str(pk))
        if len(batch) < 1000:
            break
        offset += 1000
    return ids


async def delete_all(
    client: httpx.AsyncClient,
    base: str,
    key: str,
    table: str,
) -> tuple[int | None, str | None]:
    """Retourne (nb supprimé, erreur). None count = table absente."""
    before = await count_rows(client, base, key, table)
    if before is None:
        return None, None
    if before == 0:
        return 0, None

    ids = await fetch_ids(client, base, key, table)
    if ids is None:
        return None, None
    if not ids:
        return 0, None

    url = f"{base}/{table}"
    deleted = 0
    chunk = 80
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        in_list = ",".join(part)
        resp = await client.delete(
            url,
            headers=_headers(key),
            params={"id": f"in.({in_list})"},
        )
        if resp.status_code >= 400:
            return deleted, f"DELETE HTTP {resp.status_code}: {resp.text[:300]}"
        deleted += len(part)

    after = await count_rows(client, base, key, table)
    if after not in (0, None) and after > 0:
        return deleted, f"Il reste {after} ligne(s) après suppression"

    return deleted, None


async def main() -> None:
    settings = get_settings()
    url = (settings.supabase_url or "").strip().rstrip("/")
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        print("ERREUR: SUPABASE_URL / SUPABASE_SECRET_KEY manquants")
        sys.exit(1)

    base = f"{url}/rest/v1"
    report: dict[str, dict] = {}

    # Ordre FK : prérequis puis cibles dans ordre sûr
    delete_order = PREREQ_TABLES + [
        "demos",
        "generations",
        "managed_projects",
        "projects",
        "ecommerce_products",
        "devis",
        "factures",
        "transactions",
    ]
    seen: set[str] = set()
    ordered = []
    for t in delete_order:
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    print("Vidage Supabase — tables cibles:", ", ".join(TARGET_TABLES))
    print()

    async with httpx.AsyncClient(timeout=120.0) as client:
        for table in ordered:
            is_target = table in TARGET_TABLES
            is_prereq = table in PREREQ_TABLES
            if not is_target and not is_prereq:
                continue

            try:
                n, err = await delete_all(client, base, key, table)
            except Exception as exc:
                n, err = None, str(exc)

            entry = {
                "deleted": n,
                "error": err,
                "target": is_target,
                "prerequisite": is_prereq and not is_target,
            }
            report[table] = entry

            if n is None:
                status = "ABSENTE (404)"
                if is_target:
                    print(f"  {table}: {status}")
            elif err:
                print(f"  {table}: ERREUR — {err} (partiel: {n})")
            elif is_prereq:
                if n:
                    print(f"  {table}: {n} ligne(s) (prérequis FK)")
            else:
                print(f"  {table}: {n} ligne(s) supprimée(s)")

    print("\n=== CONFIRMATION (tables cibles) ===")
    total = 0
    for table in TARGET_TABLES:
        entry = report.get(table, {"deleted": None, "error": "non traitée"})
        n = entry.get("deleted")
        err = entry.get("error")
        if n is None:
            print(f"  {table}: inaccessible (404) — 0 confirmé côté REST")
        elif err:
            print(f"  {table}: {n} supprimée(s) — ATTENTION: {err}")
            total += n or 0
        else:
            print(f"  {table}: {n} ligne(s) supprimée(s) — table vide")
            total += n or 0

    print(f"\nTotal lignes supprimées (tables cibles): {total}")

    out = Path(__file__).parent / "_truncate_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
