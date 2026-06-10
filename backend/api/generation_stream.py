"""
Store d'événements SSE en RAM pour le pipeline de génération v2.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

CLEANUP_DELAY_SECONDS = 300
STREAM_TIMEOUT_SECONDS = 900

TRACKED_AGENTS: tuple[tuple[str, int], ...] = (
    ("BriefAI", 1),
    ("GeneratorAI", 2),
    ("SupervisorAI", 3),
    ("DeployAI", 4),
)
TRACKED_TOTAL = 4


@dataclass
class GenerationSession:
    queue: asyncio.Queue[tuple[int, str, dict[str, Any]] | None] = field(
        default_factory=asyncio.Queue
    )
    history: list[tuple[int, str, dict[str, Any]]] = field(default_factory=list)
    seq: int = 0
    terminal: bool = False
    subscribers: int = 0
    cleanup_task: asyncio.Task[None] | None = None
    notify: asyncio.Event = field(default_factory=asyncio.Event)


class GenerationEventStore:
    """Sessions de génération — historique + file pour SSE (reconnexion sans doublons)."""

    def __init__(self) -> None:
        self._sessions: dict[str, GenerationSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, generation_id: str) -> None:
        async with self._lock:
            self._sessions[generation_id] = GenerationSession()

    def exists(self, generation_id: str) -> bool:
        return generation_id in self._sessions

    def get_queue(self, generation_id: str) -> asyncio.Queue[tuple[int, str, dict[str, Any]] | None] | None:
        session = self._sessions.get(generation_id)
        if session is None:
            return None
        return session.queue

    def get_session(self, generation_id: str) -> GenerationSession | None:
        return self._sessions.get(generation_id)

    async def emit(
        self,
        generation_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        session = self._sessions.get(generation_id)
        if session is None:
            return

        session.seq += 1
        payload = dict(data or {})
        record = (session.seq, event_type, payload)
        session.history.append(record)
        await session.queue.put(record)
        session.notify.set()
        session.notify = asyncio.Event()

        if event_type in ("done", "error"):
            session.terminal = True
            self._schedule_cleanup(generation_id)

    async def emit_log(self, generation_id: str, message: str) -> None:
        await self.emit(generation_id, "log", {"message": message})

    def _schedule_cleanup(self, generation_id: str) -> None:
        session = self._sessions.get(generation_id)
        if session is None or session.cleanup_task is not None:
            return

        async def _delayed_cleanup() -> None:
            try:
                await asyncio.sleep(CLEANUP_DELAY_SECONDS)
            except asyncio.CancelledError:
                return
            await self.cleanup(generation_id)

        try:
            loop = asyncio.get_running_loop()
            session.cleanup_task = loop.create_task(_delayed_cleanup())
        except RuntimeError:
            pass

    async def cleanup(self, generation_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(generation_id, None)
        if session is None:
            return
        if session.cleanup_task and not session.cleanup_task.done():
            session.cleanup_task.cancel()
        await session.queue.put(None)

    def register_subscriber(self, generation_id: str) -> bool:
        session = self._sessions.get(generation_id)
        if session is None:
            return False
        session.subscribers += 1
        return True

    def unregister_subscriber(self, generation_id: str) -> None:
        session = self._sessions.get(generation_id)
        if session is None:
            return
        session.subscribers = max(0, session.subscribers - 1)
        if session.subscribers == 0 and not session.terminal:
            logger.info(
                "[generation_stream] client déconnecté avant fin generation_id=%s",
                generation_id,
            )

    async def iter_events(
        self,
        generation_id: str,
        *,
        after_seq: int = 0,
        timeout_seconds: float = STREAM_TIMEOUT_SECONDS,
    ):
        """Itère les événements (replay historique + nouveaux) pour SSE."""
        session = self._sessions.get(generation_id)
        if session is None:
            return

        last_sent = after_seq
        deadline = asyncio.get_running_loop().time() + timeout_seconds

        while True:
            for seq, event_type, data in session.history:
                if seq <= last_sent:
                    continue
                last_sent = seq
                yield seq, event_type, data
                if event_type in ("done", "error"):
                    return

            if session.terminal and last_sent >= session.seq:
                return

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                yield (
                    last_sent + 1,
                    "error",
                    {"message": "Timeout SSE génération (15 min)"},
                )
                return

            try:
                await asyncio.wait_for(session.notify.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                yield (
                    last_sent + 1,
                    "error",
                    {"message": "Timeout SSE génération (15 min)"},
                )
                return


generation_event_store = GenerationEventStore()
