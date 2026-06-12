"""
Persistance Supabase — Multi-Agent Orchestration (sessions, contexte, messages).
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

SESSION_SELECT = (
    "id,generation_id,project_id,organization_id,workflow_id,status,"
    "agents_planned,agents_completed,agents_failed,parallel_groups,"
    "total_agents,started_at,completed_at,created_at"
)

CONTEXT_SELECT = (
    "id,session_id,context_key,context_value,produced_by,created_at,updated_at"
)

MESSAGE_SELECT = (
    "id,session_id,sender_agent,receiver_agent,message_type,payload,status,"
    "channel_name,priority,created_at"
)

CHANNEL_SELECT = "id,channel_name,channel_type,description,created_at"

ANALYTICS_SELECT = (
    "id,period_date,channel_name,messages_sent,messages_acked,"
    "avg_latency_ms,updated_at"
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


class OrchestrationStore:
    """CRUD PostgREST pour agent_sessions / shared_contexts / agent_messages."""

    def __init__(self, supabase: SupabaseStore | None = None) -> None:
        self._supabase = supabase or get_supabase_store()

    def is_configured(self) -> bool:
        return self._supabase.is_configured()

    def _rest_url(self) -> str:
        return self._supabase._rest_url()

    async def create_session(
        self,
        generation_id: str,
        workflow_id: str,
        agents_planned: list[str],
        *,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not generation_id.strip():
            return None

        now = _now_iso()
        planned = list(agents_planned or [])
        body: dict[str, Any] = {
            "generation_id": generation_id.strip(),
            "organization_id": DEFAULT_ORG_ID,
            "workflow_id": (workflow_id or "").strip(),
            "status": "created",
            "agents_planned": planned,
            "agents_completed": [],
            "agents_failed": [],
            "parallel_groups": [],
            "total_agents": len(planned),
            "started_at": now,
        }
        if project_id:
            body["project_id"] = str(project_id).strip()

        url = f"{self._rest_url()}/agent_sessions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "create_session", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[OrchestrationStore] create_session ignoré — %s", exc)
            return None

    async def update_session(
        self,
        generation_id: str,
        *,
        status: str | None = None,
        agents_completed: list[str] | None = None,
        agents_failed: list[str] | None = None,
        current_agent: str | None = None,
        parallel_groups: list[list[str]] | None = None,
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not generation_id.strip():
            return None

        body: dict[str, Any] = {}
        if status is not None:
            body["status"] = status.strip()
        if agents_completed is not None:
            body["agents_completed"] = list(agents_completed)
        if agents_failed is not None:
            body["agents_failed"] = list(agents_failed)
        if parallel_groups is not None:
            body["parallel_groups"] = parallel_groups
        if current_agent is not None:
            body["status"] = "running"

        if not body:
            return None

        url = f"{self._rest_url()}/agent_sessions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"generation_id": f"eq.{generation_id.strip()}"},
                    json=body,
                )
            _raise_for_status(resp, "update_session", "PATCH", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[OrchestrationStore] update_session ignoré — %s", exc)
            return None

    async def complete_session(
        self,
        generation_id: str,
        status: str = "completed",
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not generation_id.strip():
            return None

        body: dict[str, Any] = {
            "status": status.strip(),
            "completed_at": _now_iso(),
        }

        url = f"{self._rest_url()}/agent_sessions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    params={"generation_id": f"eq.{generation_id.strip()}"},
                    json=body,
                )
            _raise_for_status(resp, "complete_session", "PATCH", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[OrchestrationStore] complete_session ignoré — %s", exc)
            return None

    async def get_session(self, generation_id: str) -> dict[str, Any] | None:
        if not self.is_configured() or not generation_id.strip():
            return None

        url = f"{self._rest_url()}/agent_sessions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "generation_id": f"eq.{generation_id.strip()}",
                    "select": SESSION_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_session", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def list_sessions(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        params: dict[str, str] = {
            "select": SESSION_SELECT,
            "order": "created_at.desc",
            "limit": str(max(1, min(limit, 100))),
        }
        if project_id:
            params["project_id"] = f"eq.{project_id.strip()}"
        if status:
            params["status"] = f"eq.{status.strip()}"

        url = f"{self._rest_url()}/agent_sessions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "list_sessions", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def set_shared_context(
        self,
        session_id: str,
        context_key: str,
        context_value: Any,
        produced_by: str,
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not session_id.strip() or not context_key.strip():
            return None

        now = _now_iso()
        body: dict[str, Any] = {
            "session_id": session_id.strip(),
            "context_key": context_key.strip(),
            "context_value": context_value,
            "produced_by": produced_by.strip(),
            "updated_at": now,
        }

        url = f"{self._rest_url()}/shared_contexts"
        headers = self._supabase._headers("return=representation,resolution=merge-duplicates")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=headers,
                    params={"on_conflict": "session_id,context_key"},
                    json=body,
                )
            _raise_for_status(resp, "set_shared_context", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[OrchestrationStore] set_shared_context ignoré — %s", exc)
            return None

    async def get_shared_context(
        self,
        session_id: str,
        context_key: str,
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not session_id.strip() or not context_key.strip():
            return None

        url = f"{self._rest_url()}/shared_contexts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "session_id": f"eq.{session_id.strip()}",
                    "context_key": f"eq.{context_key.strip()}",
                    "select": CONTEXT_SELECT,
                    "limit": "1",
                },
            )
            _raise_for_status(resp, "get_shared_context", "GET", url, self._supabase)
            return _first_row(resp.json())

    async def list_shared_contexts(self, session_id: str) -> list[dict[str, Any]]:
        if not self.is_configured() or not session_id.strip():
            return []

        url = f"{self._rest_url()}/shared_contexts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "session_id": f"eq.{session_id.strip()}",
                    "select": CONTEXT_SELECT,
                    "order": "created_at.asc",
                },
            )
            _raise_for_status(resp, "list_shared_contexts", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def send_message(
        self,
        session_id: str,
        sender_agent: str,
        message_type: str,
        payload: dict[str, Any] | None = None,
        *,
        receiver_agent: str | None = None,
        channel_name: str = "pipeline_events",
        priority: str = "normal",
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not session_id.strip():
            return None

        body: dict[str, Any] = {
            "session_id": session_id.strip(),
            "sender_agent": sender_agent.strip(),
            "message_type": message_type.strip(),
            "payload": payload or {},
            "status": "sent",
            "channel_name": (channel_name or "pipeline_events").strip(),
            "priority": (priority or "normal").strip(),
        }
        if receiver_agent:
            body["receiver_agent"] = receiver_agent.strip()

        url = f"{self._rest_url()}/agent_messages"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
            _raise_for_status(resp, "send_message", "POST", url, self._supabase)
            return _first_row(resp.json())
        except Exception as exc:
            logger.warning("[OrchestrationStore] send_message ignoré — %s", exc)
            return None

    async def get_messages(
        self,
        session_id: str,
        *,
        receiver_agent: str | None = None,
        channel_name: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_configured() or not session_id.strip():
            return []

        params: dict[str, str] = {
            "session_id": f"eq.{session_id.strip()}",
            "select": MESSAGE_SELECT,
            "order": "created_at.asc",
        }
        if receiver_agent:
            params["receiver_agent"] = f"eq.{receiver_agent.strip()}"
        if channel_name:
            params["channel_name"] = f"eq.{channel_name.strip()}"

        url = f"{self._rest_url()}/agent_messages"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._supabase._headers(), params=params)
            _raise_for_status(resp, "get_messages", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def list_channels(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/communication_channels"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={"select": CHANNEL_SELECT, "order": "channel_name.asc"},
            )
            _raise_for_status(resp, "list_channels", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def ack_message(
        self,
        message_id: str,
        agent_id: str,
        *,
        status: str = "received",
    ) -> dict[str, Any] | None:
        if not self.is_configured() or not message_id.strip() or not agent_id.strip():
            return None

        body = {
            "message_id": message_id.strip(),
            "agent_id": agent_id.strip(),
            "status": status.strip(),
        }
        url = f"{self._rest_url()}/message_acks"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    headers=self._supabase._headers("return=representation"),
                    json=body,
                )
                _raise_for_status(resp, "ack_message", "POST", url, self._supabase)
                row = _first_row(resp.json())
                if row:
                    msg_resp = await client.get(
                        f"{self._rest_url()}/agent_messages",
                        headers=self._supabase._headers(),
                        params={
                            "id": f"eq.{message_id.strip()}",
                            "select": "channel_name",
                            "limit": "1",
                        },
                    )
                    if msg_resp.status_code == 200:
                        msg_row = _first_row(msg_resp.json())
                        channel = str(
                            (msg_row or {}).get("channel_name") or "pipeline_events"
                        )
                        await self.increment_analytics(channel, messages_acked=1)
                return row
        except Exception as exc:
            logger.warning("[OrchestrationStore] ack_message ignoré — %s", exc)
            return None

    async def increment_analytics(
        self,
        channel_name: str,
        *,
        messages_sent: int = 0,
        messages_acked: int = 0,
        latency_ms: float = 0,
    ) -> None:
        if not self.is_configured():
            return

        period = datetime.now(UTC).date().isoformat()
        channel = (channel_name or "pipeline_events").strip()
        url = f"{self._rest_url()}/communication_analytics"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    url,
                    headers=self._supabase._headers(),
                    params={
                        "period_date": f"eq.{period}",
                        "channel_name": f"eq.{channel}",
                        "select": ANALYTICS_SELECT,
                        "limit": "1",
                    },
                )
                existing = _first_row(resp.json()) if resp.status_code == 200 else None

                if existing:
                    sent = int(existing.get("messages_sent") or 0) + messages_sent
                    acked = int(existing.get("messages_acked") or 0) + messages_acked
                    prev_avg = float(existing.get("avg_latency_ms") or 0)
                    if messages_sent > 0 and latency_ms > 0:
                        prev_sent = int(existing.get("messages_sent") or 0)
                        avg = ((prev_avg * prev_sent) + latency_ms) / max(sent, 1)
                    else:
                        avg = prev_avg
                    patch = await client.patch(
                        url,
                        headers=self._supabase._headers(),
                        params={"id": f"eq.{existing['id']}"},
                        json={
                            "messages_sent": sent,
                            "messages_acked": acked,
                            "avg_latency_ms": round(avg, 2),
                            "updated_at": _now_iso(),
                        },
                    )
                    _raise_for_status(patch, "increment_analytics", "PATCH", url, self._supabase)
                else:
                    post = await client.post(
                        url,
                        headers=self._supabase._headers(),
                        json={
                            "period_date": period,
                            "channel_name": channel,
                            "messages_sent": messages_sent,
                            "messages_acked": messages_acked,
                            "avg_latency_ms": round(latency_ms, 2) if latency_ms else 0,
                            "updated_at": _now_iso(),
                        },
                    )
                    _raise_for_status(post, "increment_analytics", "POST", url, self._supabase)
        except Exception as exc:
            logger.warning("[OrchestrationStore] increment_analytics ignoré — %s", exc)

    async def get_communication_analytics(
        self,
        *,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/communication_analytics"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._supabase._headers(),
                params={
                    "select": ANALYTICS_SELECT,
                    "order": "period_date.desc",
                    "limit": str(max(1, min(days, 365))),
                },
            )
            _raise_for_status(resp, "get_communication_analytics", "GET", url, self._supabase)
            rows = resp.json()
            return rows if isinstance(rows, list) else []

    async def get_stats(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "avg_agents_per_session": 0.0,
                "parallel_executions_count": 0,
            }

        sessions = await self.list_sessions(limit=100)
        total = len(sessions)
        completed = sum(1 for s in sessions if s.get("status") == "completed")
        failed = sum(1 for s in sessions if s.get("status") == "failed")
        agent_counts = [len(s.get("agents_completed") or []) for s in sessions]
        avg_agents = sum(agent_counts) / total if total else 0.0
        parallel_count = sum(
            1
            for s in sessions
            if isinstance(s.get("parallel_groups"), list) and len(s["parallel_groups"]) > 0
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "avg_agents_per_session": round(avg_agents, 2),
            "parallel_executions_count": parallel_count,
        }


_store: OrchestrationStore | None = None


def get_orchestration_store() -> OrchestrationStore:
    global _store
    if _store is None:
        _store = OrchestrationStore()
    return _store


def reset_orchestration_store() -> None:
    global _store
    _store = None
