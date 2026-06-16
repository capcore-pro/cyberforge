"""
Persistance Supabase — client_reviews (Mode Client).
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx

from config import Settings, get_settings
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)

logger = logging.getLogger(__name__)

ReviewStatus = Literal["pending", "approved", "revision_requested"]
RespondStatus = Literal["approved", "revision_requested"]


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _review_public_url(token: str, settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    base = cfg.frontend_public_url.rstrip("/")
    return f"{base}/review/{token}"


class ClientReviewStore:
    """CRUD PostgREST pour client_reviews."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def create_review(
        self,
        project_id: str,
        client_name: str | None = None,
        client_email: str | None = None,
        *,
        expires_days: int = 30,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        pid = project_id.strip()
        if not pid:
            raise SupabaseStoreError("project_id requis.")

        token = secrets.token_urlsafe(32)
        days = max(1, min(int(expires_days or 30), 365))
        expires_at = (datetime.now(UTC) + timedelta(days=days)).isoformat()

        body: dict[str, Any] = {
            "project_id": pid,
            "token": token,
            "status": "pending",
            "expires_at": expires_at,
        }
        if client_name and client_name.strip():
            body["client_name"] = client_name.strip()[:255]
        if client_email and client_email.strip():
            body["client_email"] = client_email.strip()[:255]

        url = f"{self._rest_url()}/client_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "create_client_review", "POST", url, self._supabase)
            _raise_for_status(resp, "create_client_review", "POST", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Création review sans réponse.")

        return {
            "id": str(row["id"]),
            "token": str(row["token"]),
            "url": _review_public_url(str(row["token"]), self._settings),
            "expires_at": str(row["expires_at"]),
        }

    async def get_review_by_token(self, token: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        clean = token.strip()
        if not clean:
            return None
        url = f"{self._rest_url()}/client_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"token": f"eq.{clean}", "limit": "1"},
            )
            _raise_for_status(resp, "get_client_review", "GET", url, self._supabase)
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            return rows[0]

    async def mark_viewed(self, token: str) -> None:
        review = await self.get_review_by_token(token)
        if not review or review.get("viewed_at"):
            return
        clean = token.strip()
        url = f"{self._rest_url()}/client_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=minimal"),
                params={"token": f"eq.{clean}"},
                json={"viewed_at": _now_iso()},
            )
            _raise_for_status(resp, "mark_client_review_viewed", "PATCH", url, self._supabase)

    async def submit_feedback(
        self,
        token: str,
        status: RespondStatus,
        feedback: str | None = None,
        rating: int | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        review = await self.get_review_by_token(token)
        if not review:
            raise SupabaseStoreError("Review introuvable.")

        if self._is_expired(review):
            raise SupabaseStoreError("Ce lien a expiré.")

        current_status = str(review.get("status") or "pending")
        if current_status != "pending" or review.get("responded_at"):
            raise SupabaseStoreError("Réponse déjà enregistrée.")

        patch: dict[str, Any] = {
            "status": status,
            "responded_at": _now_iso(),
        }
        if feedback and feedback.strip():
            patch["feedback"] = feedback.strip()[:8000]
        if rating is not None:
            patch["rating"] = max(1, min(int(rating), 5))

        clean = token.strip()
        url = f"{self._rest_url()}/client_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers("return=representation"),
                params={"token": f"eq.{clean}"},
                json=patch,
            )
            _raise_for_status(resp, "submit_client_review", "PATCH", url, self._supabase)
            row = _first_row(resp.json())
            if not row:
                raise SupabaseStoreError("Mise à jour review sans réponse.")
            return row

    async def list_reviews(self, project_id: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        pid = project_id.strip()
        if not pid:
            return []
        url = f"{self._rest_url()}/client_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "project_id": f"eq.{pid}",
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(resp, "list_client_reviews", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    @staticmethod
    def _is_expired(review: dict[str, Any]) -> bool:
        raw = review.get("expires_at")
        if not raw:
            return False
        try:
            expires = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            return datetime.now(UTC) >= expires
        except ValueError:
            return False


_store: ClientReviewStore | None = None


def get_client_review_store() -> ClientReviewStore:
    global _store
    if _store is None:
        _store = ClientReviewStore()
    return _store


def reset_client_review_store() -> None:
    global _store
    _store = None
