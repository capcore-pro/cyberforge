"""
Contrat commun des outils externes — Tool Framework V2.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolRequest:
    action: str
    payload: dict = field(default_factory=dict)
    agent_id: str | None = None
    project_id: str | None = None
    generation_id: str | None = None


@dataclass
class ToolResult:
    success: bool
    output: dict = field(default_factory=dict)
    duration_ms: int = 0
    error_message: str | None = None
    tool_id: str = ""
    action: str = ""


async def _log_tool_execution(request: ToolRequest, result: ToolResult) -> None:
    try:
        from db.tool_store import get_tool_store

        store = get_tool_store()
        if not store.is_configured():
            return
        metadata: dict | None = None
        if result.output:
            metadata = {"output_keys": list(result.output.keys())}
        await store.record_execution(
            result.tool_id,
            result.action,
            "success" if result.success else "failure",
            agent_id=request.agent_id,
            project_id=request.project_id,
            generation_id=request.generation_id,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
            metadata=metadata,
        )
    except Exception as exc:
        logger.warning("[BaseTool] log exécution ignoré — %s", exc)


class BaseTool(ABC):
    tool_id: str
    name: str
    category: str

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResult:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    async def run(self, request: ToolRequest) -> ToolResult:
        """Wrapper autour de execute() avec mesure, catch et log non bloquant."""
        start = time.perf_counter()
        try:
            result = await self.execute(request)
            result.duration_ms = int((time.perf_counter() - start) * 1000)
            result.tool_id = self.tool_id
            result.action = request.action
        except Exception as exc:
            result = ToolResult(
                success=False,
                error_message=str(exc),
                duration_ms=int((time.perf_counter() - start) * 1000),
                tool_id=self.tool_id,
                action=request.action,
            )
        asyncio.create_task(_log_tool_execution(request, result))
        return result
