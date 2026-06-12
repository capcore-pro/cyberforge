"""
Persistance Supabase — LLM usage (lignes) + cost_tracking (agrégats journaliers).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

import httpx

from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
    get_supabase_store,
)
from tools.llm_pricing import compute_llm_cost_usd

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _first_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        row = data[0]
        return row if isinstance(row, dict) else None
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


class LLMUsageStore:
    """CRUD PostgREST pour llm_usage et cost_tracking."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def record(
        self,
        *,
        agent_name: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int = 0,
        project_id: str | None = None,
        generation_id: str | None = None,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any] | None:
        """Insère une ligne llm_usage et met à jour l'agrégat journalier."""
        if not self.is_configured():
            return None

        inp = max(0, int(input_tokens or 0))
        out = max(0, int(output_tokens or 0))
        total = inp + out
        cost_usd = compute_llm_cost_usd(provider, model, inp, out)

        body: dict[str, Any] = {
            "agent_name": agent_name.strip(),
            "provider": provider.strip(),
            "model": model.strip(),
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": total,
            "cost_usd": cost_usd,
            "duration_ms": max(0, int(duration_ms or 0)),
            "organization_id": organization_id,
        }
        if project_id:
            body["project_id"] = project_id
        if generation_id:
            body["generation_id"] = generation_id

        url = f"{self._rest_url()}/llm_usage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "record_llm_usage", "POST", url, self._supabase)
            _raise_for_status(resp, "record_llm_usage", "POST", url, self._supabase)
            row = _first_row(resp.json())

        try:
            await self._upsert_daily_aggregate(
                cost_usd=cost_usd,
                total_tokens=total,
                organization_id=organization_id,
            )
        except Exception as exc:
            logger.warning("[LLMUsageStore] agrégat journalier ignoré — %s", exc)

        return row

    async def link_project(
        self,
        generation_id: str,
        project_id: str,
    ) -> None:
        """Associe les lignes d'une génération SSE au project_id Supabase."""
        if not self.is_configured():
            return
        gid = (generation_id or "").strip()
        pid = (project_id or "").strip()
        if not gid or not pid:
            return

        url = f"{self._rest_url()}/llm_usage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers=self._supabase._headers(),
                params={"generation_id": f"eq.{gid}"},
                json={"project_id": pid},
            )
            _raise_for_status(resp, "link_llm_usage_project", "PATCH", url, self._supabase)

    async def _upsert_daily_aggregate(
        self,
        *,
        cost_usd: float,
        total_tokens: int,
        organization_id: str = DEFAULT_ORG_ID,
        period: str = "day",
    ) -> None:
        today = date.today()
        url = f"{self._rest_url()}/cost_tracking"
        params = {
            "organization_id": f"eq.{organization_id}",
            "period": f"eq.{period}",
            "period_date": f"eq.{today.isoformat()}",
            "select": "id,total_cost_usd,total_tokens,generations_count",
            "limit": "1",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params=params,
            )
            _raise_for_status(get_resp, "get_cost_tracking", "GET", url, self._supabase)
            rows = get_resp.json()
            if isinstance(rows, list) and rows:
                row = rows[0]
                row_id = str(row.get("id") or "")
                new_cost = float(row.get("total_cost_usd") or 0) + float(cost_usd)
                new_tokens = int(row.get("total_tokens") or 0) + int(total_tokens)
                patch_resp = await client.patch(
                    url,
                    headers=self._supabase._headers(),
                    params={"id": f"eq.{row_id}"},
                    json={
                        "total_cost_usd": round(new_cost, 6),
                        "total_tokens": new_tokens,
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                )
                _raise_for_status(
                    patch_resp, "patch_cost_tracking", "PATCH", url, self._supabase
                )
                return

            post_resp = await client.post(
                url,
                headers=self._supabase._headers("return=representation"),
                json={
                    "organization_id": organization_id,
                    "period": period,
                    "period_date": today.isoformat(),
                    "total_cost_usd": round(float(cost_usd), 6),
                    "total_tokens": int(total_tokens),
                    "generations_count": 0,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
            _raise_for_status(
                post_resp, "insert_cost_tracking", "POST", url, self._supabase
            )

    async def increment_generation_count(
        self,
        *,
        organization_id: str = DEFAULT_ORG_ID,
        period: str = "day",
    ) -> None:
        """Incrémente generations_count pour la journée (fin de pipeline réussi)."""
        if not self.is_configured():
            return
        today = date.today()
        url = f"{self._rest_url()}/cost_tracking"
        params = {
            "organization_id": f"eq.{organization_id}",
            "period": f"eq.{period}",
            "period_date": f"eq.{today.isoformat()}",
            "select": "id,generations_count",
            "limit": "1",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(url, headers=self._supabase._headers(), params=params)
            if get_resp.status_code >= 400:
                return
            rows = get_resp.json()
            if not isinstance(rows, list) or not rows:
                await client.post(
                    url,
                    headers=self._supabase._headers(),
                    json={
                        "organization_id": organization_id,
                        "period": period,
                        "period_date": today.isoformat(),
                        "total_cost_usd": 0,
                        "total_tokens": 0,
                        "generations_count": 1,
                    },
                )
                return
            row_id = str(rows[0].get("id") or "")
            count = int(rows[0].get("generations_count") or 0) + 1
            await client.patch(
                url,
                headers=self._supabase._headers(),
                params={"id": f"eq.{row_id}"},
                json={
                    "generations_count": count,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )

    async def get_daily_summary(
        self,
        *,
        period_date: date | None = None,
        organization_id: str = DEFAULT_ORG_ID,
        period: str = "day",
    ) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "generations_count": 0,
                "period_date": (period_date or date.today()).isoformat(),
            }

        target = period_date or date.today()
        url = f"{self._rest_url()}/cost_tracking"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "organization_id": f"eq.{organization_id}",
                    "period": f"eq.{period}",
                    "period_date": f"eq.{target.isoformat()}",
                    "select": "total_cost_usd,total_tokens,generations_count,period_date",
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_daily_summary", "GET", url, self._supabase)
            rows = resp.json()
            if isinstance(rows, list) and rows:
                row = rows[0]
                return {
                    "total_cost_usd": float(row.get("total_cost_usd") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "generations_count": int(row.get("generations_count") or 0),
                    "period_date": str(row.get("period_date") or target.isoformat()),
                }
        return {
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "generations_count": 0,
            "period_date": target.isoformat(),
        }

    async def list_by_generation(self, generation_id: str) -> list[dict[str, Any]]:
        if not self.is_configured() or not generation_id.strip():
            return []
        url = f"{self._rest_url()}/llm_usage"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "generation_id": f"eq.{generation_id}",
                    "select": "*",
                    "order": "created_at.asc",
                },
            )
            _raise_for_status(resp, "list_llm_usage", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_dashboard_llm_stats(
        self,
        *,
        organization_id: str = DEFAULT_ORG_ID,
    ) -> dict[str, Any]:
        """Agrégats mensuels (par agent) + série journalière pour le dashboard."""
        empty: dict[str, Any] = {
            "monthly": {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "by_agent": [],
            },
            "daily": [],
        }
        if not self.is_configured():
            return empty

        today = date.today()
        month_start = date(today.year, today.month, 1)
        month_start_iso = f"{month_start.isoformat()}T00:00:00Z"

        usage_url = f"{self._rest_url()}/llm_usage"
        tracking_url = f"{self._rest_url()}/cost_tracking"

        async with httpx.AsyncClient(timeout=30.0) as client:
            usage_resp = await client.get(
                usage_url,
                headers=self._supabase._headers(),
                params={
                    "organization_id": f"eq.{organization_id}",
                    "created_at": f"gte.{month_start_iso}",
                    "select": "agent_name,cost_usd,total_tokens",
                    "order": "created_at.desc",
                    "limit": "5000",
                },
            )
            _raise_for_status(usage_resp, "list_llm_usage_month", "GET", usage_url, self._supabase)
            usage_rows = usage_resp.json()
            if not isinstance(usage_rows, list):
                usage_rows = []

            tracking_resp = await client.get(
                tracking_url,
                headers=self._supabase._headers(),
                params={
                    "organization_id": f"eq.{organization_id}",
                    "period": "eq.day",
                    "period_date": f"gte.{month_start.isoformat()}",
                    "select": "period_date,total_cost_usd,total_tokens",
                    "order": "period_date.asc",
                    "limit": "31",
                },
            )
            _raise_for_status(
                tracking_resp, "list_cost_tracking_month", "GET", tracking_url, self._supabase
            )
            tracking_rows = tracking_resp.json()
            if not isinstance(tracking_rows, list):
                tracking_rows = []

        by_agent_map: dict[str, dict[str, float | int]] = {}
        total_cost = 0.0
        total_tokens = 0
        for row in usage_rows:
            if not isinstance(row, dict):
                continue
            agent = str(row.get("agent_name") or "unknown").strip() or "unknown"
            cost = float(row.get("cost_usd") or 0)
            tokens = int(row.get("total_tokens") or 0)
            total_cost += cost
            total_tokens += tokens
            bucket = by_agent_map.setdefault(
                agent, {"agent": agent, "cost_usd": 0.0, "tokens": 0}
            )
            bucket["cost_usd"] = float(bucket["cost_usd"]) + cost
            bucket["tokens"] = int(bucket["tokens"]) + tokens

        by_agent = sorted(
            [
                {
                    "agent": str(item["agent"]),
                    "cost_usd": round(float(item["cost_usd"]), 6),
                    "tokens": int(item["tokens"]),
                }
                for item in by_agent_map.values()
            ],
            key=lambda x: x["cost_usd"],
            reverse=True,
        )

        daily = [
            {
                "date": str(row.get("period_date") or ""),
                "cost_usd": round(float(row.get("total_cost_usd") or 0), 6),
                "tokens": int(row.get("total_tokens") or 0),
            }
            for row in tracking_rows
            if isinstance(row, dict)
        ]

        return {
            "monthly": {
                "total_cost_usd": round(total_cost, 6),
                "total_tokens": total_tokens,
                "by_agent": by_agent,
            },
            "daily": daily,
        }


_store: LLMUsageStore | None = None


def get_llm_usage_store() -> LLMUsageStore:
    global _store
    if _store is None:
        _store = LLMUsageStore()
    return _store


def reset_llm_usage_store() -> None:
    global _store
    _store = None
