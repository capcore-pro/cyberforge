"""
Contrats agents CyberForge — résultat structuré ou erreur explicite.

PRINCIPE : pas de succès partiel silencieux.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AgentFailure(BaseModel):
    """Échec explicite — toujours journalisé et propagé."""

    agent_id: str
    code: str
    message: str
    detail: str | None = None

    def to_exception(self) -> "AgentContractError":
        return AgentContractError(
            agent_id=self.agent_id,
            code=self.code,
            message=self.message,
            detail=self.detail,
        )


class AgentResult(BaseModel, Generic[T]):
    """
    Enveloppe standard de sortie agent.
    `ok` False ⇒ `error` est obligatoire ; `data` doit être None.
    """

    agent_id: str
    agent_name: str
    status: AgentStatus
    data: T | None = None
    error: AgentFailure | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == AgentStatus.SUCCESS

    @classmethod
    def success(
        cls,
        *,
        agent_id: str,
        agent_name: str,
        data: T,
        meta: dict[str, Any] | None = None,
    ) -> "AgentResult[T]":
        return cls(
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentStatus.SUCCESS,
            data=data,
            error=None,
            meta=meta or {},
        )

    @classmethod
    def failure(
        cls,
        *,
        agent_id: str,
        agent_name: str,
        code: str,
        message: str,
        detail: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "AgentResult[T]":
        return cls(
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentStatus.FAILURE,
            data=None,
            error=AgentFailure(
                agent_id=agent_id,
                code=code,
                message=message,
                detail=detail,
            ),
            meta=meta or {},
        )


class AgentContractError(RuntimeError):
    """Levée quand un agent ne peut pas remplir sa responsabilité unique."""

    def __init__(
        self,
        *,
        agent_id: str,
        code: str,
        message: str,
        detail: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(f"[{agent_id}] {code}: {message}")


def require_ok(result: AgentResult[T]) -> T:
    """Extrait les données ou lève l'erreur contractuelle."""
    if result.ok and result.data is not None:
        return result.data
    if result.error:
        raise result.error.to_exception()
    raise AgentContractError(
        agent_id=result.agent_id,
        code="invalid_result",
        message="Résultat agent invalide (ni data ni error).",
    )
