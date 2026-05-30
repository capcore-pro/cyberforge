"""Quick row counts via PostgREST HEAD + Prefer: count=exact."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings, plain_secret_str  # noqa: E402

TABLES = [
    "clients",
    "projects",
    "generations",
    "demos",
    "managed_projects",
    "notifications",
    "transactions",
    "devis",
    "factures",
    "ecommerce_products",
    "reservations",
]


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
    }


def count_table(client: httpx.Client, rest_base: str, key: str, table: str) -> tuple[str, str]:
    url = f"{rest_base}/{table}"
    for select_col in ("id", "*"):
        resp = client.head(url, headers=_headers(key), params={"select": select_col})
        if resp.status_code == 404:
            return table, "N/A (404)"
        if resp.status_code >= 400:
            continue
        cr = resp.headers.get("content-range") or ""
        if "/" in cr:
            total = cr.split("/")[-1]
            try:
                return table, str(int(total))
            except ValueError:
                return table, total
        return table, "0"
    return table, f"ERR {resp.status_code}"


def main() -> None:
    settings = get_settings()
    url = (settings.supabase_url or "").strip().rstrip("/")
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        print("ERREUR: SUPABASE_URL et SUPABASE_SECRET_KEY requis (backend config)")
        sys.exit(1)

    rest_base = f"{url}/rest/v1"
    print(f"{'table':<24} {'count':>10}")
    print("-" * 36)

    with httpx.Client(timeout=60.0) as client:
        for table in TABLES:
            name, count = count_table(client, rest_base, key, table)
            print(f"{name:<24} {count:>10}")


if __name__ == "__main__":
    main()
