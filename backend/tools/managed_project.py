"""
Abstraction V2+ — projets gérés (tous types).

On garde une API uniforme : create/update/delete + un store commun (Supabase).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

from config import Settings
from db.managed_projects_store import ManagedProjectsStore

ManagedProjectType = Literal[
    "vitrine_next",
    "application_web",
    "extension_navigateur",
    "application_desktop",
    "api_backend",
]


@dataclass(frozen=True)
class ManagedActionContext:
    project_id: str
    run_id: str
    action: Literal["create", "update", "delete"]
    prompt: str | None = None


class ManagedProjectProvisioner(ABC):
    """
    Contrat : un provisioner sait appliquer les actions pour un type de projet.
    """

    @property
    @abstractmethod
    def project_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def provision_create(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def provision_update(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def provision_delete(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
        hard_delete: bool,
    ) -> dict[str, Any]:
        raise NotImplementedError

