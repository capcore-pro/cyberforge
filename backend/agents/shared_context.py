"""
Contexte partagé entre agents du pipeline LangGraph.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

OpenHandsStatus = Literal["pending", "analyzing", "correcting", "done", "skipped"]


@dataclass
class SharedContext:
    """État partagé du pipeline — persistance inter-nœuds LangGraph."""

    # OpenHands — Auto-correction
    openhands_enabled: bool = True
    openhands_iterations: int = 0
    openhands_max_iterations: int = 3
    openhands_issues_found: list[Any] = field(default_factory=list)
    openhands_corrections_applied: list[Any] = field(default_factory=list)
    openhands_status: OpenHandsStatus = "pending"
    openhands_report: dict[str, Any] = field(default_factory=dict)
    openhands_quality_before: float = 0.0
    openhands_quality_after: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SharedContext:
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})
