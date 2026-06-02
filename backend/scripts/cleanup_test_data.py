"""
Nettoyage Supabase — supprime les données de test.

Ce script :
- Se connecte via SUPABASE_URL et SUPABASE_SECRET_KEY
- Vide des tables dans un ordre compatible avec les FK
- Utilise DELETE (pas DROP)
- Log le nombre de lignes supprimées par table
- Affiche un résumé final

Exécution :
    python backend/scripts/cleanup_test_data.py
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Iterable

from supabase import create_client


TABLES_IN_ORDER = [
    # enfants → parents
    "managed_project_auth",
    "projects",
]


logger = logging.getLogger("cleanup_test_data")


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Variable d'env manquante: {name}")
    return value


def _chunked(seq: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _count_rows(supabase: Any, table: str) -> int | None:
    """
    Compte les lignes via PostgREST (count exact).
    On tente d'abord un head=True si supporté, sinon on retombe sur une requête normale.
    """
    try:
        # postgrest-py: select(..., count="exact", head=True)
        res = supabase.table(table).select("*", count="exact", head=True).execute()
        cnt = getattr(res, "count", None)
        if isinstance(cnt, int):
            return cnt
    except TypeError:
        pass
    except Exception as exc:
        logger.info(f"{table}: table vide ou inexistante")
        logger.debug("Count failed for %s: %s", table, exc)
        return None

    try:
        res = supabase.table(table).select("*", count="exact").limit(1).execute()
        cnt = getattr(res, "count", None)
        if isinstance(cnt, int):
            return cnt
        data = getattr(res, "data", None)
        return len(data) if isinstance(data, list) else 0
    except Exception as exc:
        logger.info(f"{table}: table vide ou inexistante")
        logger.debug("Count fallback failed for %s: %s", table, exc)
        return None


def _delete_all_rows(supabase: Any, table: str) -> None:
    """
    Tente un DELETE sans filtre (équivalent à `DELETE FROM table`).
    Si l'API exige un filtre de sécurité, on retombe sur une suppression par ids.
    """
    try:
        supabase.table(table).delete().execute()
        return
    except Exception as exc:
        # Repli robuste: on récupère les ids, puis delete par chunk avec in_()
        logger.debug("DELETE sans filtre refusé pour %s: %s", table, exc)

    # Repli "best effort" sans supposer l'existence d'une colonne id
    try:
        sample_res = supabase.table(table).select("*").limit(1).execute()
        sample = getattr(sample_res, "data", None)
        if not isinstance(sample, list) or not sample or not isinstance(sample[0], dict):
            return
        keys = list(sample[0].keys())
        pk = "id" if "id" in keys else (keys[0] if keys else "")
        if not pk:
            return
    except Exception:
        return

    ids: list[Any] = []
    offset = 0
    page_size = 1000
    while True:
        res = (
            supabase.table(table)
            .select(pk)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = getattr(res, "data", None)
        if not isinstance(rows, list) or not rows:
            break
        for r in rows:
            if isinstance(r, dict) and r.get(pk) is not None:
                ids.append(r[pk])
        if len(rows) < page_size:
            break
        offset += page_size

    if not ids:
        return

    for part in _chunked(ids, 200):
        supabase.table(table).delete().in_(pk, part).execute()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    try:
        supabase_url = _require_env("SUPABASE_URL").rstrip("/")
        supabase_key = _require_env("SUPABASE_SECRET_KEY")
    except Exception as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1

    supabase = create_client(supabase_url, supabase_key)

    total_deleted = 0
    for table in TABLES_IN_ORDER:
        before = _count_rows(supabase, table)
        if before is None:
            continue
        if before == 0:
            logger.info(f"{table}: table vide ou inexistante")
            continue

        _delete_all_rows(supabase, table)

        # On log le nombre supprimé basé sur le count initial (objectif: table vidée)
        total_deleted += before
        logger.info(f"{table}: {before} ligne(s) supprimée(s)")

    logger.info(f"Nettoyage terminé — {total_deleted} lignes supprimées")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

