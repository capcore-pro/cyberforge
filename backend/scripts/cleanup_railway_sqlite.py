"""
Nettoyage Railway + SQLite local.

PARTIE 1 (Railway)
- Liste les déploiements d'un projet Railway via GraphQL
- Supprime uniquement ceux dont status != "ACTIVE"
- NE SUPPRIME PAS le déploiement ACTIVE

PARTIE 2 (SQLite)
- Trouve la DB locale: backend/cyberforge.db (fallback: backend/data/cyberforge.db)
- Liste les tables
- DELETE FROM {table} pour chaque table (pas DROP), en ignorant sqlite_*

Résumé final: Railway X déploiements supprimés + SQLite Y lignes supprimées
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import requests


RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"
RAILWAY_PROJECT_ID = "2e4a2e4a-b2d9-4506-bbec-5d5471aabdc5"


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Variable d'env manquante: {name}")
    return value


def _railway_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _railway_post(token: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    r = requests.post(
        RAILWAY_GRAPHQL_URL,
        headers=_railway_headers(token),
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("errors"):
        raise RuntimeError(f"Railway GraphQL errors: {json.dumps(data['errors'], ensure_ascii=False)[:2000]}")
    return data if isinstance(data, dict) else {"data": data}


def cleanup_railway() -> int:
    token = _require_env("RAILWAY_API_KEY")

    q = """
{
  deployments(input: { projectId: "2e4a2e4a-b2d9-4506-bbec-5d5471aabdc5" }) {
    edges {
      node {
        id
        status
        createdAt
        url
      }
    }
  }
}
""".strip()

    resp = _railway_post(token, q)
    edges = ((resp.get("data") or {}).get("deployments") or {}).get("edges") or []
    if not isinstance(edges, list):
        edges = []

    deleted = 0
    for e in edges:
        node = e.get("node") if isinstance(e, dict) else None
        if not isinstance(node, dict):
            continue
        deployment_id = str(node.get("id") or "").strip()
        status = str(node.get("status") or "").strip()
        url = str(node.get("url") or "").strip()
        if not deployment_id:
            continue

        if status == "ACTIVE":
            continue

        print(f"{deployment_id} {status} {url}".strip())

        m = f'mutation {{ deploymentRemove(id: "{deployment_id}") }}'
        remove_resp = _railway_post(token, m)
        remove_val: Any = None
        if isinstance(remove_resp, bool):
            remove_val = remove_resp
        elif isinstance(remove_resp, dict):
            remove_val = (remove_resp.get("data") or {}).get("deploymentRemove")

        if remove_val is False:
            print(f"{deployment_id}: déjà supprimé")

        deleted += 1

    return deleted


def _find_sqlite_db() -> Path:
    backend = Path(__file__).resolve().parents[1]
    candidates = [
        backend / "cockpit.db",
        backend / "data" / "cockpit.db",
        backend / "cyberforge.db",
        backend / "data" / "cyberforge.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "DB SQLite introuvable: " + " ou ".join(str(p) for p in candidates)
    )


def cleanup_sqlite() -> int:
    db_path = _find_sqlite_db()
    total_deleted = 0

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [str(r[0]) for r in cur.fetchall() if r and r[0]]

        for table in tables:
            if table.startswith("sqlite_"):
                continue

            try:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                before = int(cur.fetchone()[0])
            except Exception:
                # table or view weirdness; still try to delete
                before = 0

            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()

            if before:
                print(f"{table}: {before} ligne(s) supprimée(s)")
                total_deleted += before
            else:
                # If count failed, fall back to cursor.rowcount when available
                n = cur.rowcount if isinstance(cur.rowcount, int) and cur.rowcount >= 0 else 0
                print(f"{table}: {n} ligne(s) supprimée(s)")
                total_deleted += n

    finally:
        conn.close()

    return total_deleted


def main() -> int:
    railway_deleted = cleanup_railway()
    sqlite_deleted = cleanup_sqlite()

    print(f"Résumé — Railway {railway_deleted} déploiements supprimés + SQLite {sqlite_deleted} lignes supprimées")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

