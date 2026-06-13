"""
Persistance Supabase — Pipeline Commercial (prospects, interactions).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

STATUTS = [
    "nouveau",
    "contacté",
    "démo_envoyée",
    "négociation",
    "gagné",
    "perdu",
]

PROSPECT_SELECT = (
    "id,organization_id,nom,entreprise,email,telephone,secteur,source,statut,"
    "valeur_estimee,notes,demo_url,contact_date,relance_date,closed_date,"
    "created_at,updated_at"
)

INTERACTION_SELECT = "id,prospect_id,type,notes,created_at"

UPDATABLE_FIELDS = frozenset(
    {
        "nom",
        "entreprise",
        "email",
        "telephone",
        "secteur",
        "source",
        "statut",
        "valeur_estimee",
        "notes",
        "demo_url",
        "contact_date",
        "relance_date",
        "closed_date",
    }
)


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


def _parse_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


class ProspectStore:
    """CRUD PostgREST pour prospects / prospect_interactions."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_all(self, statut: str | None = None) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": PROSPECT_SELECT,
            "order": "created_at.desc",
        }
        if statut:
            params["statut"] = f"eq.{statut.strip()}"

        url = f"{self._rest_url()}/prospects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url, headers=self._supabase._headers(), params=params
            )
            _raise_for_status(resp, "list_prospects", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_by_id(self, prospect_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not prospect_id.strip():
            return None

        url = f"{self._rest_url()}/prospects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{prospect_id.strip()}",
                    "select": PROSPECT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_prospect", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def create(
        self,
        nom: str,
        entreprise: str | None = None,
        email: str | None = None,
        telephone: str | None = None,
        secteur: str | None = None,
        source: str = "manuel",
        valeur_estimee: float = 0,
        notes: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "nom": nom.strip(),
            "organization_id": DEFAULT_ORG_ID,
            "source": (source or "manuel").strip(),
            "statut": "nouveau",
            "valeur_estimee": valeur_estimee,
        }
        if entreprise:
            body["entreprise"] = entreprise.strip()
        if email:
            body["email"] = email.strip()
        if telephone:
            body["telephone"] = telephone.strip()
        if secteur:
            body["secteur"] = secteur.strip()
        if notes:
            body["notes"] = notes.strip()

        url = f"{self._rest_url()}/prospects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_prospect", "POST", url, self._supabase)
            _raise_for_status(resp, "create_prospect", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création prospect sans identifiant retourné.")
            return row

    async def update(self, prospect_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body = {
            key: value
            for key, value in updates.items()
            if key in UPDATABLE_FIELDS and value is not None
        }
        body["updated_at"] = _now_iso()

        url = f"{self._rest_url()}/prospects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{prospect_id.strip()}"},
                json=body,
            )
            _raise_for_status(resp, "update_prospect", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Prospect introuvable.")
            return row

    async def move_statut(self, prospect_id: str, new_statut: str) -> dict[str, Any]:
        statut = new_statut.strip()
        if statut not in STATUTS:
            raise SupabaseStoreError(f"Statut invalide : {statut}")

        updates: dict[str, Any] = {"statut": statut}
        now = _now_iso()
        if statut == "gagné":
            updates["closed_date"] = now
        if statut == "contacté":
            updates["contact_date"] = now

        return await self.update(prospect_id, updates)

    async def delete(self, prospect_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/prospects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{prospect_id.strip()}"},
            )
            _raise_for_status(resp, "delete_prospect", "DELETE", url, self._supabase)
            return True

    async def add_interaction(
        self,
        prospect_id: str,
        type_interaction: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "prospect_id": prospect_id.strip(),
            "type": type_interaction.strip(),
        }
        if notes:
            body["notes"] = notes.strip()

        url = f"{self._rest_url()}/prospect_interactions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._supabase._headers("return=representation"),
                json=body,
            )
            _raise_for_status(resp, "add_interaction", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Interaction sans identifiant retourné.")
            return row

    async def get_interactions(self, prospect_id: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/prospect_interactions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "prospect_id": f"eq.{prospect_id.strip()}",
                    "select": INTERACTION_SELECT,
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(resp, "get_interactions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(self) -> dict[str, Any]:
        rows = await self.list_all()
        par_statut: dict[str, dict[str, Any]] = {
            s: {"count": 0, "valeur": 0.0} for s in STATUTS
        }

        total_valeur = 0.0
        gagnes = 0
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prospects_ce_mois = 0

        for row in rows:
            statut = str(row.get("statut") or "nouveau")
            valeur = _parse_float(row.get("valeur_estimee"))
            bucket = par_statut.setdefault(statut, {"count": 0, "valeur": 0.0})
            bucket["count"] += 1
            bucket["valeur"] = round(bucket["valeur"] + valeur, 2)

            if statut != "perdu":
                total_valeur += valeur
            if statut == "gagné":
                gagnes += 1

            created_raw = row.get("created_at")
            if created_raw:
                try:
                    created = datetime.fromisoformat(
                        str(created_raw).replace("Z", "+00:00")
                    )
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=UTC)
                    if created >= month_start:
                        prospects_ce_mois += 1
                except ValueError:
                    pass

        total = len(rows)
        taux = round((gagnes / total) * 100, 1) if total else 0.0

        return {
            "par_statut": par_statut,
            "total_prospects": total,
            "valeur_pipeline": round(total_valeur, 2),
            "taux_conversion": taux,
            "prospects_ce_mois": prospects_ce_mois,
        }


_prospect_store: ProspectStore | None = None


def get_prospect_store() -> ProspectStore:
    global _prospect_store
    if _prospect_store is None:
        _prospect_store = ProspectStore()
    return _prospect_store
