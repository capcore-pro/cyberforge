from __future__ import annotations

from typing import Any

from config import Settings
from db.managed_projects_store import ManagedProjectsStore
from tools.managed_extension_service import hard_delete_extension, provision_extension, update_extension
from tools.managed_project import ManagedActionContext, ManagedProjectProvisioner


class ExtensionNavigateurProvisioner(ManagedProjectProvisioner):
    @property
    def project_type(self) -> str:
        return "extension_navigateur"

    async def provision_create(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
    ) -> dict[str, Any]:
        await provision_extension(
            project_id=ctx.project_id,
            run_id=ctx.run_id,
            prompt=ctx.prompt or "",
            settings=settings,
            store=store,
        )
        return {"ok": True}

    async def provision_update(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
    ) -> dict[str, Any]:
        await update_extension(
            project_id=ctx.project_id,
            prompt=ctx.prompt or "",
            settings=settings,
            store=store,
        )
        return {"ok": True}

    async def provision_delete(
        self,
        *,
        ctx: ManagedActionContext,
        settings: Settings,
        store: ManagedProjectsStore,
        hard_delete: bool,
    ) -> dict[str, Any]:
        if hard_delete:
            await hard_delete_extension(project_id=ctx.project_id, settings=settings, store=store)
        return {"ok": True}

