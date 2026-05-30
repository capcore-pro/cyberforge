"""
Routes Mode Client — fiches clients et historique des démos.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.clients_store import (
    ClientDetail,
    ClientDemoSummary,
    ClientKind,
    ClientRow,
    ClientsStore,
    DemoStatusSlug,
    get_clients_store,
)
from db.demos_store import SupabaseStoreError, _normalize_status, _parse_iso, get_demos_store
from tools.demo_urls import unlock_demo_url

logger = logging.getLogger(__name__)

from cache import ttl_cache

router = APIRouter(tags=["clients"])


def _sync_legal_client(
    *,
    name: str,
    email: str | None,
    phone: str | None,
    address: str | None,
    siret: str | None,
    legal_client_id: str | None,
) -> str | None:
    """Crée ou met à jour la fiche légale SQLite liée (devis / factures)."""
    try:
        import legal_db

        legal_db.init_legal_db()
        email_clean = (email or "").strip() or "contact@capcore.local"
        if legal_client_id:
            legal_db.update_client(
                legal_client_id,
                name=name.strip(),
                email=email_clean,
                phone=phone,
                address=address,
                siret=siret,
            )
            return legal_client_id
        created = legal_db.add_client(
            name=name.strip(),
            email=email_clean,
            phone=phone,
            address=address,
            siret=siret,
        )
        return str(created["id"])
    except Exception:
        logger.exception("Sync fiche légale client échouée")
        return legal_client_id


class ClientCreateRequest(BaseModel):
    kind: ClientKind = Field(
        default="client",
        description="client = fiche commerciale ; perso = créations Mat",
    )
    name: str = Field(..., min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    siret: str | None = Field(default=None, max_length=20)
    active: bool = True
    primary_color: str | None = Field(default=None, max_length=16)
    logo_url: str | None = Field(default=None, max_length=600_000)


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    siret: str | None = Field(default=None, max_length=20)
    active: bool | None = None
    primary_color: str | None = Field(default=None, max_length=16)
    logo_url: str | None = Field(default=None, max_length=600_000)


class ClientBrandingResponse(BaseModel):
    """Branding pour pré-remplir une seed de démo."""

    client_id: str
    kind: ClientKind = "client"
    name: str
    company: str | None = None
    primary_color: str | None = None
    logo_data_url: str | None = None


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    status = 502
    if detail.get("status_code") == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


def _effective_demo_status(
  status: DemoStatusSlug,
  *,
  expired: bool,
) -> DemoStatusSlug:
    if expired and status not in ("expiree", "validee"):
        return "expiree"
    return status


@router.get("/clients", response_model=list[ClientRow])
@ttl_cache(seconds=30.0)
async def list_clients(kind: ClientKind | None = None) -> list[ClientRow]:
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        return await store.list_clients(kind=kind)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /clients") from exc


@router.post("/clients", response_model=ClientRow)
async def create_client(body: ClientCreateRequest) -> ClientRow:
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        legal_id = _sync_legal_client(
            name=body.name,
            email=body.email,
            phone=body.phone,
            address=body.address,
            siret=body.siret,
            legal_client_id=None,
        )
        return await store.create_client(
            name=body.name,
            company=body.company,
            email=body.email,
            phone=body.phone,
            address=body.address,
            siret=body.siret,
            active=body.active,
            legal_client_id=legal_id,
            primary_color=body.primary_color,
            logo_url=body.logo_url,
            kind=body.kind,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /clients") from exc


@router.get("/clients/{client_id}", response_model=ClientDetail)
async def get_client_detail(client_id: str) -> ClientDetail:
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})

    try:
        client = await store.get_by_id(client_id)
        if client is None:
            raise HTTPException(status_code=404, detail="Client introuvable.")
        raw_demos = await store.list_demos_for_client(client_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /clients/{id}") from exc

    summaries: list[ClientDemoSummary] = []
    for row in raw_demos:
        if not isinstance(row, dict):
            continue
        token = str(row.get("token") or "")
        expires_at = str(row.get("expires_at") or "")
        expired = False
        if expires_at:
            try:
                expired = datetime.now(UTC) >= _parse_iso(expires_at)
            except ValueError:
                expired = False

        status = _effective_demo_status(
            _normalize_status(row.get("status")),
            expired=expired,
        )
        summaries.append(
            ClientDemoSummary(
                id=str(row.get("id") or ""),
                token=token,
                title=str(row.get("title") or "Démo"),
                status=status,
                created_at=str(row.get("created_at") or ""),
                expires_at=expires_at,
                opened_at=str(row["opened_at"]) if row.get("opened_at") else None,
                unlock_url=unlock_demo_url(token) if token else None,
            )
        )

    return ClientDetail(**client.model_dump(), demos=summaries)


@router.patch("/clients/{client_id}", response_model=ClientRow)
async def update_client(client_id: str, body: ClientUpdateRequest) -> ClientRow:
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        existing = await store.get_by_id(client_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Client introuvable.")

        merged_name = body.name if body.name is not None else existing.name
        merged_email = body.email if body.email is not None else existing.email
        merged_phone = body.phone if body.phone is not None else existing.phone
        merged_address = body.address if body.address is not None else existing.address
        merged_siret = body.siret if body.siret is not None else existing.siret

        legal_id = _sync_legal_client(
            name=merged_name,
            email=merged_email,
            phone=merged_phone,
            address=merged_address,
            siret=merged_siret,
            legal_client_id=existing.legal_client_id,
        )

        updated = await store.update_client(
            client_id,
            name=body.name,
            company=body.company,
            email=body.email,
            phone=body.phone,
            address=body.address,
            siret=body.siret,
            active=body.active,
            legal_client_id=legal_id,
            primary_color=body.primary_color,
            logo_url=body.logo_url,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "PATCH /clients/{id}") from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    return updated


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str) -> dict[str, bool]:
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        existing = await store.get_by_id(client_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Client introuvable.")
        await store.delete_client(client_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "DELETE /clients/{id}") from exc
    return {"deleted": True}


@router.get("/clients/{client_id}/branding", response_model=ClientBrandingResponse)
async def client_branding_for_demo(client_id: str) -> ClientBrandingResponse:
    """Seed branding — couleur principale et logo pour création de démo."""
    store = get_clients_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail={"message": "Supabase non configuré."})
    try:
        client = await store.get_by_id(client_id)
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "GET /clients/{id}/branding") from exc

    if client is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    logo_data: str | None = None
    if client.logo_url and client.logo_url.strip().startswith("data:image/"):
        logo_data = client.logo_url.strip()

    return ClientBrandingResponse(
        client_id=client.id,
        kind=client.kind,
        name=client.name,
        company=client.company,
        primary_color=client.primary_color,
        logo_data_url=logo_data,
    )
