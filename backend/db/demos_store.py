"""
Persistance Supabase — démos client (lien public + mot de passe temporaire).
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast

from db.demo_types import DemoStatusSlug

import bcrypt
import httpx
from pydantic import BaseModel, Field

from db.demo_password import generate_demo_password
from tools.demo_preview_html import build_demo_preview_html
from tools.generation_sources import is_usable_preview_html, normalize_generation_sources
from tools.standalone_demo_html import is_fresh_task_preview_html

if TYPE_CHECKING:
    from db.supabase_store import SupabaseStore


def _supabase():
    """Import tardif — évite le cycle supabase_store ↔ demos_store (via agents)."""
    import db.supabase_store as store

    return store


def __getattr__(name: str) -> Any:
    if name == "SupabaseStoreError":
        return _supabase().SupabaseStoreError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

logger = logging.getLogger(__name__)

DemoDuration = Literal["24h", "48h", "7d"]

DURATION_HOURS: dict[DemoDuration, int] = {
    "24h": 24,
    "48h": 48,
    "7d": 168,
}


class InterestContact(BaseModel):
    """Soumission formulaire CapCore sur une démo."""

    name: str
    email: str
    message: str


class DemoPayload(BaseModel):
    """Livrable figé servi au client (HTML rendu, lecture seule)."""

    preview_html: str = Field(..., min_length=1, max_length=500_000)
    cloudflare_url: str | None = Field(default=None, max_length=512)
    cloudflare_path: str | None = Field(default=None, max_length=256)
    cloudflare_hash: str | None = Field(default=None, max_length=64)
    cloudflare_project: str | None = Field(default=None, max_length=64)
    summary: str | None = None
    project_type: str | None = None
    access_password_enc: str | None = Field(
        default=None,
        max_length=512,
        description="Mot de passe démo chiffré (notifications équipe).",
    )


class DemoRow(BaseModel):
    id: str
    token: str
    title: str
    expires_at: str
    duration_hours: int
    payload: DemoPayload
    generation_id: str | None = None
    client_id: str | None = None
    status: DemoStatusSlug = "envoyee"
    opened_at: str | None = None
    interested_at: str | None = None
    interest_seen_at: str | None = None
    interest_contact: dict[str, str] | None = None
    created_at: str


class DemoContactNotification(BaseModel):
    """Résumé pour badge / toast CyberForge."""

    id: str
    token: str
    title: str
    interested_at: str | None
    interest_contact: dict[str, str] | None = None


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
        self._supabase = supabase or _supabase().get_supabase_store()

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
        client_id: str | None = None,
        status: DemoStatusSlug = "envoyee",
        token: str | None = None,
        password: str | None = None,
    ) -> DemoCreated:
        if not self.is_configured():
            raise _supabase().SupabaseStoreError(
                "Supabase non configuré : impossible de créer une démo."
            )

        hours = DURATION_HOURS[duration]
        expires_at = datetime.now(UTC) + timedelta(hours=hours)
        password = (password or "").strip() or generate_demo_password()
        password_hash = self.hash_password(password)
        token = (token or "").strip() or self._new_token()

        body = {
            "token": token,
            "password_hash": password_hash,
            "expires_at": expires_at.isoformat(),
            "duration_hours": hours,
            "title": title.strip() or "Démo CyberForge",
            "payload": payload.model_dump(),
            "generation_id": generation_id,
            "client_id": client_id,
            "status": status,
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
                _supabase()._raise_transport_error(exc, "create_demo", "POST", url, self._supabase)

            _supabase()._raise_for_status(resp, "create_demo", "POST", url, self._supabase)
            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            if not isinstance(row, dict):
                raise _supabase().SupabaseStoreError("Création démo sans identifiant retourné.")

            return DemoCreated(
                id=str(row["id"]),
                token=str(row["token"]),
                password=password,
                expires_at=str(row["expires_at"]),
                duration_hours=int(row["duration_hours"]),
                title=str(row["title"]),
            )

    async def list_cloudflare_manifest_entries(
        self,
        *,
        exclude_token: str | None = None,
    ) -> dict[str, str]:
        """Chemins actifs (non expirés) → hash pour manifest Pages fusionné."""
        if not self.is_configured():
            return {}

        now_iso = datetime.now(UTC).isoformat()
        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "expires_at": f"gt.{now_iso}",
                    "select": "token,payload",
                },
            )
            _supabase()._raise_for_status(resp, "list_demos_manifest", "GET", url, self._supabase)
            rows = resp.json()

        entries: dict[str, str] = {}
        if not isinstance(rows, list):
            return entries

        for row in rows:
            if not isinstance(row, dict):
                continue
            token = str(row.get("token") or "")
            if exclude_token and token == exclude_token:
                continue
            raw = row.get("payload")
            if not isinstance(raw, dict):
                continue
            path = raw.get("cloudflare_path")
            digest = raw.get("cloudflare_hash")
            if isinstance(path, str) and path.strip() and isinstance(digest, str) and digest.strip():
                entries[path.strip()] = digest.strip()
        return entries

    async def find_by_generation_id(self, generation_id: str) -> DemoRow | None:
        """Démo client liée à une génération Supabase (au plus une)."""
        if not self.is_configured() or not generation_id.strip():
            return None

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "generation_id": f"eq.{generation_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
            _supabase()._raise_for_status(
                resp, "find_demo_by_generation", "GET", url, self._supabase
            )
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _demo_from_row(rows[0])

    async def get_by_id(self, demo_id: str) -> DemoRow | None:
        if not self.is_configured():
            return None

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{demo_id}", "select": "*"},
            )
            _supabase()._raise_for_status(resp, "get_demo_by_id", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _demo_from_row(rows[0])

    async def delete_demo(self, demo_id: str) -> bool:
        if not self.is_configured():
            raise _supabase().SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                url,
                headers=self._supabase._headers("return=minimal"),
                params={"id": f"eq.{demo_id}"},
            )
            _supabase()._raise_for_status(resp, "delete_demo", "DELETE", url, self._supabase)
        return True

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
            _supabase()._raise_for_status(resp, "get_demo", "GET", url, self._supabase)
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
            _supabase()._raise_for_status(resp, "get_generation_for_demo", "GET", url, self._supabase)
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

    async def record_interested(
        self,
        token: str,
        *,
        contact: InterestContact | None = None,
    ) -> DemoRow | None:
        """Marque la démo comme « intéressée » (formulaire CapCore soumis)."""
        row = await self.get_by_token(token)
        if row is None or self.is_expired(row):
            return None
        if row.status == "expiree":
            return None

        from datetime import UTC, datetime

        interested_at = datetime.now(UTC).isoformat()
        patch: dict[str, Any] = {
            "status": "interessee",
            "interested_at": interested_at,
            "interest_seen_at": None,
        }
        if contact is not None:
            patch["interest_contact"] = {
                "name": contact.name.strip(),
                "email": contact.email.strip(),
                "message": contact.message.strip(),
            }

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"token": f"eq.{token.strip()}"},
                json=patch,
            )
            _supabase()._raise_for_status(resp, "record_demo_interested", "PATCH", url, self._supabase)
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return _demo_from_row(rows[0])
        return row.model_copy(
            update={
                "status": "interessee",
                "interested_at": interested_at,
                "interest_seen_at": None,
                "interest_contact": patch.get("interest_contact"),
            }
        )

    async def list_unread_contact_notifications(self) -> list[DemoContactNotification]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "status": "eq.interessee",
                    "interest_seen_at": "is.null",
                    "interested_at": "not.is.null",
                    "select": "id,token,title,interested_at,interest_contact",
                    "order": "interested_at.desc",
                },
            )
            _supabase()._raise_for_status(
                resp, "list_unread_contact_notifications", "GET", url, self._supabase
            )
            rows = resp.json()
        if not isinstance(rows, list):
            return []
        out: list[DemoContactNotification] = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            contact = raw.get("interest_contact")
            out.append(
                DemoContactNotification(
                    id=str(raw.get("id") or ""),
                    token=str(raw.get("token") or ""),
                    title=str(raw.get("title") or "Démo"),
                    interested_at=str(raw["interested_at"])
                    if raw.get("interested_at")
                    else None,
                    interest_contact=contact if isinstance(contact, dict) else None,
                )
            )
        return out

    async def count_unread_contact_notifications(self) -> int:
        items = await self.list_unread_contact_notifications()
        return len(items)

    async def mark_contact_notifications_seen(self) -> int:
        if not self.is_configured():
            return 0

        from datetime import UTC, datetime

        seen_at = datetime.now(UTC).isoformat()
        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={
                    "status": "eq.interessee",
                    "interest_seen_at": "is.null",
                },
                json={"interest_seen_at": seen_at},
            )
            _supabase()._raise_for_status(
                resp, "mark_contact_notifications_seen", "PATCH", url, self._supabase
            )
            rows = resp.json()
        if isinstance(rows, list):
            return len(rows)
        return 0

    async def record_open(self, token: str) -> DemoRow | None:
        """Marque la démo comme ouverte (première ouverture depuis « envoyée »)."""
        row = await self.get_by_token(token)
        if row is None or self.is_expired(row):
            return None
        if row.status not in ("envoyee",):
            return row

        from datetime import UTC, datetime

        opened_at = datetime.now(UTC).isoformat()
        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"token": f"eq.{token.strip()}"},
                json={"status": "ouverte", "opened_at": opened_at},
            )
            _supabase()._raise_for_status(resp, "record_demo_open", "PATCH", url, self._supabase)
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return _demo_from_row(rows[0])
        return replace_row_open(row, opened_at)

    async def update_status(
        self,
        demo_id: str,
        status: DemoStatusSlug,
    ) -> DemoRow | None:
        if not self.is_configured():
            raise _supabase().SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{demo_id}"},
                json={"status": status},
            )
            _supabase()._raise_for_status(resp, "update_demo_status", "PATCH", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _demo_from_row(rows[0])

    async def update_client_id(
        self,
        demo_id: str,
        client_id: str | None,
    ) -> DemoRow | None:
        """Associe ou dissocie un client à une démo."""
        if not self.is_configured():
            raise _supabase().SupabaseStoreError("Supabase non configuré.")

        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"id": f"eq.{demo_id.strip()}"},
                json={"client_id": client_id.strip() if client_id else None},
            )
            _supabase()._raise_for_status(resp, "update_demo_client", "PATCH", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return _demo_from_row(rows[0])

    async def _fetch_password_hash(self, token: str) -> str | None:
        url = f"{self._rest_url()}/demos"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"token": f"eq.{token}", "select": "password_hash"},
            )
            _supabase()._raise_for_status(resp, "get_demo_hash", "GET", url, self._supabase)
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
                cloudflare_url=raw.get("cloudflare_url"),
                cloudflare_path=raw.get("cloudflare_path"),
                cloudflare_hash=raw.get("cloudflare_hash"),
                cloudflare_project=raw.get("cloudflare_project"),
                summary=raw.get("summary"),
                project_type=raw.get("project_type"),
                access_password_enc=raw.get("access_password_enc"),
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
        cloudflare_url=raw.get("cloudflare_url"),
        cloudflare_path=raw.get("cloudflare_path"),
        cloudflare_hash=raw.get("cloudflare_hash"),
        cloudflare_project=raw.get("cloudflare_project"),
        summary=raw.get("summary"),
        project_type=raw.get("project_type"),
        access_password_enc=raw.get("access_password_enc"),
    )


def _normalize_status(raw: Any) -> DemoStatusSlug:
    value = str(raw or "envoyee").strip().lower()
    if value in ("envoyee", "ouverte", "validee", "expiree", "interessee"):
        return cast(DemoStatusSlug, value)
    return "envoyee"


def replace_row_open(row: DemoRow, opened_at: str) -> DemoRow:
    return row.model_copy(update={"status": "ouverte", "opened_at": opened_at})


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
        client_id=str(row["client_id"]) if row.get("client_id") else None,
        status=_normalize_status(row.get("status")),
        opened_at=str(row["opened_at"]) if row.get("opened_at") else None,
        interested_at=str(row["interested_at"]) if row.get("interested_at") else None,
        interest_seen_at=str(row["interest_seen_at"])
        if row.get("interest_seen_at")
        else None,
        interest_contact=row.get("interest_contact")
        if isinstance(row.get("interest_contact"), dict)
        else None,
        created_at=str(row["created_at"]),
    )


_store: DemosStore | None = None


def get_demos_store() -> DemosStore:
    global _store
    if _store is None:
        _store = DemosStore()
    return _store
