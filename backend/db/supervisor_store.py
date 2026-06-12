"""
Persistance Supabase — Supervisor System (décisions, quality reviews).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
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

DECISION_SELECT = (
    "id,generation_id,project_id,decision_type,agent_validated,valid,"
    "quality_score,errors,warnings,attempt_number,duration_ms,created_at"
)

REVIEW_SELECT = (
    "id,generation_id,project_id,review_type,score,max_score,"
    "passed,details,created_at"
)


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


class SupervisorStore:
    """CRUD PostgREST pour supervisor_decisions / quality_reviews."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def record_decision(
        self,
        decision_type: str,
        agent_validated: str,
        valid: bool,
        quality_score: int,
        errors: list[Any] | None = None,
        warnings: list[Any] | None = None,
        *,
        attempt_number: int = 1,
        duration_ms: int = 0,
        generation_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        body: dict[str, Any] = {
            "decision_type": decision_type.strip(),
            "agent_validated": agent_validated.strip(),
            "valid": bool(valid),
            "quality_score": max(0, min(100, int(quality_score))),
            "errors": list(errors or []),
            "warnings": list(warnings or []),
            "attempt_number": max(1, int(attempt_number)),
            "duration_ms": max(0, int(duration_ms)),
        }
        if generation_id:
            body["generation_id"] = generation_id.strip()
        if project_id:
            body["project_id"] = str(project_id).strip()

        url = f"{self._rest_url()}/supervisor_decisions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "record_decision", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[SupervisorStore] record_decision ignoré — %s", exc)
            return None

    async def record_quality_review(
        self,
        review_type: str,
        score: int,
        passed: bool,
        *,
        details: dict[str, Any] | None = None,
        generation_id: str | None = None,
        project_id: str | None = None,
        max_score: int = 100,
    ) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        body: dict[str, Any] = {
            "review_type": review_type.strip(),
            "score": max(0, min(int(max_score), int(score))),
            "max_score": int(max_score),
            "passed": bool(passed),
            "details": details or {},
        }
        if generation_id:
            body["generation_id"] = generation_id.strip()
        if project_id:
            body["project_id"] = str(project_id).strip()

        url = f"{self._rest_url()}/quality_reviews"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "record_quality_review", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[SupervisorStore] record_quality_review ignoré — %s", exc)
            return None

    async def list_decisions(
        self,
        *,
        days: int = 30,
        generation_id: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        since = (datetime.now(UTC) - timedelta(days=max(1, days))).replace(tzinfo=None)
        params: dict[str, str] = {
            "select": DECISION_SELECT,
            "created_at": f"gte.{since.isoformat()}",
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 1000))),
        }
        if generation_id:
            params["generation_id"] = f"eq.{generation_id.strip()}"

        url = f"{self._rest_url()}/supervisor_decisions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_decisions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_generation_score(self, generation_id: str) -> dict[str, Any]:
        if not self.is_configured() or not generation_id.strip():
            return {
                "avg_score": 0,
                "reviews_count": 0,
                "passed_all": False,
                "details": {},
            }

        url = f"{self._rest_url()}/quality_reviews"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "generation_id": f"eq.{generation_id.strip()}",
                    "select": REVIEW_SELECT,
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(resp, "get_generation_score", "GET", url, self._supabase)
            rows = resp.json()
            reviews = rows if isinstance(rows, list) else []

        if not reviews:
            return {
                "avg_score": 0,
                "reviews_count": 0,
                "passed_all": False,
                "details": {},
            }

        scores = [int(r.get("score") or 0) for r in reviews]
        avg_score = int(sum(scores) / len(scores))
        passed_all = all(bool(r.get("passed")) for r in reviews)
        details = {
            str(r.get("review_type") or "review"): {
                "score": r.get("score"),
                "passed": r.get("passed"),
                "details": r.get("details") or {},
            }
            for r in reviews
        }
        return {
            "avg_score": avg_score,
            "reviews_count": len(reviews),
            "passed_all": passed_all,
            "details": details,
        }

    async def get_supervisor_stats(self, *, days: int = 30) -> dict[str, Any]:
        rows = await self.list_decisions(days=days)
        total = len(rows)
        if total == 0:
            return {
                "days": days,
                "total_validations": 0,
                "pass_rate": 0.0,
                "avg_quality_score": 0.0,
                "avg_attempts": 0.0,
            }

        passed = sum(1 for r in rows if r.get("valid"))
        quality_scores = [int(r.get("quality_score") or 0) for r in rows]
        attempts = [int(r.get("attempt_number") or 1) for r in rows]
        return {
            "days": days,
            "total_validations": total,
            "pass_rate": round(passed / total, 4),
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2),
            "avg_attempts": round(sum(attempts) / len(attempts), 2),
        }


_store: SupervisorStore | None = None


def get_supervisor_store() -> SupervisorStore:
    global _store
    if _store is None:
        _store = SupervisorStore()
    return _store


def reset_supervisor_store() -> None:
    global _store
    _store = None
