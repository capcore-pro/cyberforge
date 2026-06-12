"""
Orchestration LLM usage — enregistrement pipeline + totaux agrégés.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from db.llm_usage_store import LLMUsageStore, get_llm_usage_store
from tools.llm_pricing import compute_llm_cost_usd

logger = logging.getLogger(__name__)


@dataclass
class LLMUsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    agents: list[dict[str, Any]] = field(default_factory=list)

    def add(self, agent_name: str, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        inp = int(usage.get("input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        self.input_tokens += inp
        self.output_tokens += out
        self.total_tokens += inp + out
        cost = compute_llm_cost_usd(
            str(usage.get("provider") or "anthropic"),
            str(usage.get("model") or ""),
            inp,
            out,
        )
        self.estimated_cost_usd = round(self.estimated_cost_usd + cost, 6)
        self.agents.append({"agent": agent_name, **usage, "cost_usd": cost})

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "agents": list(self.agents),
        }


class LLMUsageService:
    def __init__(self, store: LLMUsageStore | None = None) -> None:
        self._store = store or get_llm_usage_store()

    async def record_agent(
        self,
        agent_name: str,
        usage: dict[str, Any] | None,
        *,
        duration_ms: int = 0,
        project_id: str | None = None,
        generation_id: str | None = None,
        totals: LLMUsageTotals | None = None,
    ) -> None:
        if not usage:
            return
        if totals is not None:
            totals.add(agent_name, usage)
        if not self._store.is_configured():
            return
        try:
            await self._store.record(
                agent_name=agent_name,
                provider=str(usage.get("provider") or "anthropic"),
                model=str(usage.get("model") or ""),
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                duration_ms=duration_ms,
                project_id=project_id,
                generation_id=generation_id,
            )
        except Exception as exc:
            logger.warning("[LLMUsageService] record %s ignoré — %s", agent_name, exc)

    async def finalize_generation(
        self,
        *,
        generation_id: str | None,
        project_id: str | None,
        success: bool,
    ) -> None:
        if not self._store.is_configured():
            return
        try:
            if generation_id and project_id:
                await self._store.link_project(generation_id, project_id)
            if success:
                await self._store.increment_generation_count()
        except Exception as exc:
            logger.warning("[LLMUsageService] finalize ignoré — %s", exc)

    async def get_daily_summary(self) -> dict[str, Any]:
        try:
            return await self._store.get_daily_summary()
        except Exception as exc:
            logger.warning("[LLMUsageService] daily summary indisponible — %s", exc)
            return {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "generations_count": 0,
            }


_service: LLMUsageService | None = None


def get_llm_usage_service() -> LLMUsageService:
    global _service
    if _service is None:
        _service = LLMUsageService()
    return _service
