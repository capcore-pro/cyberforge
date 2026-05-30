"""
Persistance Supabase — fiches clients (Mode Client).

Schéma public.clients (Supabase) :
  Base (004) : id, nom, entreprise, email, telephone, couleur, logo_url, est_perso, created_at
  Étendu (005) : adresse, siret, actif, legal_client_id
"""

from __future__ import annotations

from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from db.demo_types import MANUAL_DEMO_STATUSES, DemoStatusSlug
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

ClientKind = Literal["client", "perso"]

# Colonnes garanties par migration 004
CLIENT_BASE_SELECT = (
    "id,est_perso,nom,entreprise,email,telephone,couleur,logo_url,created_at"
)
# Colonnes ajoutées par migration 005 (comptabilité / fiche légale)
CLIENT_EXTENDED_SELECT = "adresse,siret,actif,legal_client_id"
CLIENT_LIST_SELECT = f"{CLIENT_BASE_SELECT},{CLIENT_EXTENDED_SELECT}"
CLIENT_DETAIL_SELECT = CLIENT_LIST_SELECT


class ClientRow(BaseModel):
    id: str
    kind: ClientKind = "client"
    name: str
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    siret: str | None = None
    active: bool = True
    legal_client_id: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None
    created_at: str


class ClientDemoSummary(BaseModel):
    id: str
    token: str
    title: str
    status: DemoStatusSlug
    created_at: str
    expires_at: str
    opened_at: str | None = None
    unlock_url: str | None = None


class ClientDetail(ClientRow):
    demos: list[ClientDemoSummary] = Field(default_factory=list)


class ClientsStore:
    """CRUD PostgREST pour public.clients."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def list_clients(self, *, kind: ClientKind | None = None) -> list[ClientRow]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        params: dict[str, str] = {"select": CLIENT_LIST_SELECT, "order": "created_at.desc"}
        if kind == "perso":
            params["est_perso"] = "eq.true"
        elif kind == "client":
            params["est_perso"] = "eq.false"

        url = f"{self._rest_url()}/clients"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params=params,
            )
            _raise_for_status(resp, "list_clients", "GET", url, self._supabase)
            rows = resp.json()

        if not isinstance(rows, list):
            return []
        return [_client_from_row(r) for r in rows if isinstance(r, dict)]

    async def get_by_id(self, client_id: str) -> ClientRow | None:
        if not self.is_configured() or not client_id.strip():
            return None

        url = f"{self._rest_url()}/clients"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{client_id}", "select": CLIENT_DETAIL_SELECT},
            )
            _raise_for_status(resp, "get_client", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _client_from_row(rows[0])

    async def create_client(
        self,
        *,
        name: str,
        company: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        siret: str | None = None,
        active: bool = True,
        legal_client_id: str | None = None,
        primary_color: str | None = None,
        logo_url: str | None = None,
        kind: ClientKind = "client",
    ) -> ClientRow:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body = _row_to_db(
            name=name,
            company=company,
            email=email,
            phone=phone,
            address=address,
            siret=siret,
            active=active,
            legal_client_id=legal_client_id,
            primary_color=primary_color,
            logo_url=logo_url,
            kind=kind,
        )

        url = f"{self._rest_url()}/clients"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_client", "POST", url, self._supabase)
            _raise_for_status(resp, "create_client", "POST", url, self._supabase)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            if not isinstance(row, dict):
                raise SupabaseStoreError("Création client sans identifiant retourné.")
            return _client_from_row(row)

    async def update_client(
        self,
        client_id: str,
        *,
        name: str | None = None,
        company: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        siret: str | None = None,
        active: bool | None = None,
        legal_client_id: str | None = None,
        primary_color: str | None = None,
        logo_url: str | None = None,
        kind: ClientKind | None = None,
    ) -> ClientRow | None:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        patch: dict[str, Any] = {}
        if name is not None:
            patch["nom"] = name.strip()
        if company is not None:
            patch["entreprise"] = _optional_str(company)
        if email is not None:
            patch["email"] = _optional_str(email)
        if phone is not None:
            patch["telephone"] = _optional_str(phone)
        if address is not None:
            patch["adresse"] = _optional_str(address)
        if siret is not None:
            patch["siret"] = _optional_str(siret)
        if active is not None:
            patch["actif"] = active
        if legal_client_id is not None:
            patch["legal_client_id"] = _optional_str(legal_client_id)
        if primary_color is not None:
            patch["couleur"] = _optional_str(primary_color)
        if logo_url is not None:
            patch["logo_url"] = _optional_str(logo_url)
        if kind is not None:
            patch["est_perso"] = kind == "perso"

        if not patch:
            return await self.get_by_id(client_id)

        url = f"{self._rest_url()}/clients"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{client_id}"},
                json=patch,
            )
            _raise_for_status(resp, "update_client", "PATCH", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _client_from_row(rows[0])

    async def delete_client(self, client_id: str) -> bool:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/clients"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers("return=minimal"),
                params={"id": f"eq.{client_id}"},
            )
            _raise_for_status(resp, "delete_client", "DELETE", url, self._supabase)
        return True

    async def list_demos_for_client(self, client_id: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "client_id": f"eq.{client_id}",
                    "select": "id,token,title,status,created_at,expires_at,opened_at",
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(resp, "list_client_demos", "GET", url, self._supabase)
            rows = resp.json()
        return rows if isinstance(rows, list) else []


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _kind_from_row(row: dict[str, Any]) -> ClientKind:
    if row.get("est_perso") is True:
        return "perso"
    if str(row.get("kind") or "").strip().lower() == "perso":
        return "perso"
    return "client"


def _row_to_db(
    *,
    name: str,
    company: str | None,
    email: str | None,
    phone: str | None,
    address: str | None = None,
    siret: str | None = None,
    active: bool = True,
    legal_client_id: str | None = None,
    primary_color: str | None,
    logo_url: str | None,
    kind: ClientKind,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "nom": name.strip(),
        "entreprise": _optional_str(company),
        "email": _optional_str(email),
        "telephone": _optional_str(phone),
        "couleur": _optional_str(primary_color) or "#6366f1",
        "logo_url": _optional_str(logo_url),
        "est_perso": kind == "perso",
        "actif": active,
    }
    if address is not None:
        body["adresse"] = _optional_str(address)
    if siret is not None:
        body["siret"] = _optional_str(siret)
    if legal_client_id is not None:
        body["legal_client_id"] = _optional_str(legal_client_id)
    return body


def _client_from_row(row: dict[str, Any]) -> ClientRow:
    actif_raw = row.get("actif")
    active = True if actif_raw is None else bool(actif_raw)
    return ClientRow(
        id=str(row["id"]),
        kind=_kind_from_row(row),
        name=str(row.get("nom") or row.get("name") or ""),
        company=row.get("entreprise") if row.get("entreprise") is not None else row.get("company"),
        email=row.get("email"),
        phone=row.get("telephone") if row.get("telephone") is not None else row.get("phone"),
        address=row.get("adresse") if row.get("adresse") is not None else row.get("address"),
        siret=row.get("siret"),
        active=active,
        legal_client_id=row.get("legal_client_id"),
        primary_color=row.get("couleur") if row.get("couleur") is not None else row.get("primary_color"),
        logo_url=row.get("logo_url"),
        created_at=str(row.get("created_at") or ""),
    )


def _normalize_kind(raw: Any) -> ClientKind:
    """Tests / compat — est_perso bool ou kind legacy."""
    if raw is True:
        return "perso"
    if raw is False:
        return "client"
    if str(raw or "").strip().lower() == "perso":
        return "perso"
    return "client"


_store: ClientsStore | None = None


def get_clients_store() -> ClientsStore:
    global _store
    if _store is None:
        _store = ClientsStore()
    return _store
