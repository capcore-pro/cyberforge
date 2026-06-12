"""
Bus de messages inter-agents — persistance Supabase + handlers locaux.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

MESSAGE_TYPES: dict[str, str] = {
    "correction_request": "Demande de correction avec instructions",
    "validation_passed": "Validation réussie",
    "validation_failed": "Validation échouée avec erreurs",
    "schema_ready": "Schéma BDD produit et disponible",
    "context_ready": "Contexte enrichi disponible",
    "agent_started": "Agent démarré",
    "agent_completed": "Agent terminé avec succès",
    "agent_failed": "Agent échoué",
}

Handler = Callable[[dict[str, Any]], Awaitable[None] | None]


class MessageBus:
    """
    Bus de messages inter-agents.
    Persiste dans agent_messages via orchestration_store.
    Non bloquant — fire and forget.
    """

    def __init__(self, orchestration_store: Any) -> None:
        self._store = orchestration_store
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, message_type: str, handler: Handler) -> None:
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    def publish(
        self,
        session_id: str,
        sender_agent: str,
        message_type: str,
        payload: dict[str, Any],
        *,
        receiver_agent: str | None = None,
        channel_name: str = "pipeline_events",
        priority: str = "normal",
    ) -> None:
        asyncio.create_task(
            self._persist_and_notify(
                session_id,
                sender_agent,
                message_type,
                payload,
                receiver_agent,
                channel_name,
                priority,
            )
        )

    async def _persist_and_notify(
        self,
        session_id: str,
        sender_agent: str,
        message_type: str,
        payload: dict[str, Any],
        receiver_agent: str | None,
        channel_name: str,
        priority: str,
    ) -> None:
        t0 = time.perf_counter()
        row = await self._store.send_message(
            session_id=session_id,
            sender_agent=sender_agent,
            message_type=message_type,
            payload=payload,
            receiver_agent=receiver_agent,
            channel_name=channel_name,
            priority=priority,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        if row:
            await self._store.increment_analytics(
                channel_name,
                messages_sent=1,
                latency_ms=latency_ms,
            )

        handlers = self._handlers.get(message_type, [])
        for handler in handlers:
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.warning("Handler error for %s: %s", message_type, exc)


def get_message_bus() -> MessageBus:
    from db.orchestration_store import get_orchestration_store

    return MessageBus(get_orchestration_store())


message_bus = get_message_bus()
