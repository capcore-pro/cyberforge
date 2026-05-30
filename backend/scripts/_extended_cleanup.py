"""Passe complémentaire — nettoie demos restants et tables cibles via GET direct."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_settings, plain_secret_str  # noqa: E402

FAKE = re.compile(
    r"test|demo|démo|fictif|exemple|dupont|martin|jean|fournil|lorem|"
    r"placeholder|fake|sample|mock|acme|nova studio|example\.com|boulangerie",
    re.I,
)
TRUNCATE = ["transactions", "devis", "factures", "notifications"]


def hdr(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


async def main() -> None:
    s = get_settings()
    url = s.supabase_url.rstrip("/")
    key = plain_secret_str(s.supabase_secret_key)
    base = f"{url}/rest/v1"
    out: dict = {"deleted": {}, "errors": []}

    async with httpx.AsyncClient(timeout=90.0) as c:
        for table in TRUNCATE:
            r = await c.get(f"{base}/{table}", headers=hdr(key), params={"select": "*"})
            if r.status_code == 404:
                out["deleted"][table] = "404"
                continue
            if r.status_code >= 400:
                out["errors"].append(f"{table} GET {r.status_code}")
                continue
            rows = r.json()
            if not isinstance(rows, list) or not rows:
                out["deleted"][table] = 0
                continue
            ids = [str(x["id"]) for x in rows if "id" in x]
            if ids:
                dr = await c.delete(
                    f"{base}/{table}",
                    headers=hdr(key),
                    params={"id": f"in.({','.join(ids[:100])})"},
                )
                out["deleted"][table] = len(ids) if dr.status_code < 400 else f"err {dr.status_code}"

        for table in ("demos", "projects", "clients", "ecommerce_products"):
            r = await c.get(f"{base}/{table}", headers=hdr(key), params={"select": "*"})
            if r.status_code >= 400:
                continue
            rows = r.json()
            if not isinstance(rows, list):
                continue
            ids = []
            for row in rows:
                blob = json.dumps(row, ensure_ascii=False)
                if FAKE.search(blob):
                    ids.append(str(row["id"]))
            if ids:
                for i in range(0, len(ids), 80):
                    chunk = ids[i : i + 80]
                    await c.delete(
                        f"{base}/{table}",
                        headers=hdr(key),
                        params={"id": f"in.({','.join(chunk)})"},
                    )
                out["deleted"][table] = out["deleted"].get(table, 0) + len(ids) if isinstance(out["deleted"].get(table), int) else len(ids)
                if table not in out["deleted"] or not isinstance(out["deleted"][table], int):
                    out["deleted"][table] = len(ids)

    Path(__file__).parent.joinpath("_extended_cleanup.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
