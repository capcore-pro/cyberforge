"""
Persistance Supabase — démos client (lien public + mot de passe temporaire).
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import httpx
from pydantic import BaseModel, Field

from db.demo_password import generate_demo_password
from tools.demo_preview_html import build_demo_preview_html
from tools.generation_sources import is_usable_preview_html, normalize_generation_sources
from tools.standalone_demo_html import is_fresh_task_preview_html
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

DemoDuration = Literal["24h", "48h", "7d"]

DURATION_HOURS: dict[DemoDuration, int] = {
    "24h": 24,
    "48h": 48,
    "7d": 168,
}


class DemoPayload(BaseModel):
    """Livrable figé servi au client (HTML rendu, lecture seule)."""

    preview_html: str = Field(..., min_length=1, max_length=500_000)
    summary: str | None = None
    project_type: str | None = None


class DemoRow(BaseModel):
    id: str
    token: str
    title: str
    expires_at: str
    duration_hours: int
    payload: DemoPayload
    generation_id: str | None = None
    created_at: str


class DemoCreated(BaseModel):
    """Résultat création — mot de passe en clair une seule fois."""

    id: str
    token: str
    password: str
    expires_at: str
    duration_hours: int
    title: str


class DemoMeta(BaseModel):
    """Métadonnées publiques (sans livrable)."""

    title: str
    expires_at: str
    expired: bool


class DemosStore:
    """CRUD PostgREST pour la table public.demos."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    @staticmethod
    def hash_password(password: str) -> str:
        digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return digest.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except ValueError:
            return False

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(18)

    async def create_demo(
        self,
        *,
        title: str,
        payload: DemoPayload,
        duration: DemoDuration,
        generation_id: str | None = None,
    ) -> DemoCreated:
        if not self.is_configured():
            raise SupabaseStoreError(
                "Supabase non configuré : impossible de créer une démo."
            )

        hours = DURATION_HOURS[duration]
        expires_at = datetime.now(UTC) + timedelta(hours=hours)
        password = generate_demo_password()
        password_hash = self.hash_password(password)
        token = self._new_token()

        body = {
            "token": token,
            "password_hash": password_hash,
            "expires_at": expires_at.isoformat(),
            "duration_hours": hours,
            "title": title.strip() or "Démo CyberForge",
            "payload": payload.model_dump(),
            "generation_id": generation_id,
        }

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_demo", "POST", url, self._supabase)

            _raise_for_status(resp, "create_demo", "POST", url, self._supabase)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            if not isinstance(row, dict):
                raise SupabaseStoreError("Création démo sans identifiant retourné.")

            return DemoCreated(
                id=str(row["id"]),
                token=str(row["token"]),
                password=password,
                expires_at=str(row["expires_at"]),
                duration_hours=int(row["duration_hours"]),
                title=str(row["title"]),
            )

    async def get_by_token(self, token: str) -> DemoRow | None:
        if not self.is_configured():
            return None

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"token": f"eq.{token}", "select": "*"},
            )
            _raise_for_status(resp, "get_demo", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _demo_from_row(rows[0])

    def meta_from_row(self, row: DemoRow) -> DemoMeta:
        expires = _parse_iso(row.expires_at)
        expired = datetime.now(UTC) >= expires
        return DemoMeta(
            title=row.title,
            expires_at=row.expires_at,
            expired=expired,
        )

    def is_expired(self, row: DemoRow) -> bool:
        return datetime.now(UTC) >= _parse_iso(row.expires_at)

    async def unlock(self, token: str, password: str) -> DemoRow | None:
        row = await self.get_by_token(token)
        if row is None:
            return None
        if self.is_expired(row):
            return None
        stored = await self._fetch_password_hash(token)
        if not stored or not self.verify_password(password.strip(), stored):
            return None
        return await self._refresh_preview_if_needed(row)

    async def _refresh_preview_if_needed(self, row: DemoRow) -> DemoRow:
        """Reconstruit preview_html depuis la génération liée si l'aperçu stocké est invalide ou obsolète."""
        stored = row.payload.preview_html
        if is_usable_preview_html(stored) and is_fresh_task_preview_html(stored):
            return row
        if is_usable_preview_html(stored) and "task-add-btn" in stored and "replaceChildren" in stored:
            return row
        if not row.generation_id:
            return row

        url = f"{self._rest_url()}/generations"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "id": f"eq.{row.generation_id}",
                    "select": "code,files",
                },
            )
            _raise_for_status(resp, "get_generation_for_demo", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return row
            gen = rows[0]

        files = gen.get("files") if isinstance(gen.get("files"), list) else []
        code = str(gen.get("code") or "") or None
        norm_files, norm_code = normalize_generation_sources(files, code)
        try:
            preview = build_demo_preview_html(
                norm_files,
                title=row.title,
                code=norm_code,
            )
        except Exception:
            logger.exception(
                "Impossible de régénérer l'aperçu pour la démo %s", row.token
            )
            return row

        if not is_usable_preview_html(preview):
            return row

        row.payload = DemoPayload(
            preview_html=preview,
            summary=row.payload.summary,
            project_type=row.payload.project_type,
        )
        return row

    async def _fetch_password_hash(self, token: str) -> str | None:
        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"token": f"eq.{token}", "select": "password_hash"},
            )
            _raise_for_status(resp, "get_demo_hash", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return str(rows[0].get("password_hash") or "")


def _parse_iso(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _payload_from_storage(raw: Any, *, title: str = "Démo CyberForge") -> DemoPayload:
    """Charge le payload ; migre à la volée les anciennes démos (fichiers React bruts)."""
    if not isinstance(raw, dict):
        raw = {}

    preview_html = raw.get("preview_html")
    if isinstance(preview_html, str) and preview_html.strip():
        cleaned = preview_html.strip()
        if is_usable_preview_html(cleaned):
            return DemoPayload(
                preview_html=cleaned,
                summary=raw.get("summary"),
                project_type=raw.get("project_type"),
            )

    files = raw.get("files") if isinstance(raw.get("files"), list) else []
    code = raw.get("code") if isinstance(raw.get("code"), str) else None
    norm_files, norm_code = normalize_generation_sources(files, code)
    return DemoPayload(
        preview_html=build_demo_preview_html(
            norm_files,
            title=title,
            code=norm_code,
        ),
        summary=raw.get("summary"),
        project_type=raw.get("project_type"),
    )


def _demo_from_row(row: dict[str, Any]) -> DemoRow:
    raw_payload = row.get("payload") or {}
    return DemoRow(
        id=str(row["id"]),
        token=str(row["token"]),
        title=str(row["title"]),
        expires_at=str(row["expires_at"]),
        duration_hours=int(row["duration_hours"]),
        payload=_payload_from_storage(raw_payload, title=str(row.get("title") or "Démo CyberForge")),
        generation_id=str(row["generation_id"]) if row.get("generation_id") else None,
        created_at=str(row["created_at"]),
    )


_store: DemosStore | None = None


def get_demos_store() -> DemosStore:
    global _store
    if _store is None:
        _store = DemosStore()
    return _store
