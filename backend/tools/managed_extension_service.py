"""
Managed extension_navigateur service (Chrome/Chromium).

V1: deterministic scaffold + zip artifact.
- Push sources to GitHub branch (optional but keeps persistence)
- Provide zip download from backend by re-zipping the canonical file set.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from typing import Any

from config import Settings, get_settings
from db.managed_projects_store import ManagedProjectsStore
from tools.project_deletion import hard_delete_managed_project
from tools.export_github import delete_github_branch, push_vitrine_site_to_github

logger = logging.getLogger(__name__)


class ManagedExtensionError(Exception):
    pass


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _extension_files(prompt: str, slug: str) -> dict[str, str]:
    from tools.extension_pipeline import build_extension_files

    return build_extension_files(prompt, slug=slug)


def build_extension_zip(files: dict[str, str]) -> bytes:
    from tools.extension_pipeline import build_extension_zip as _zip

    return _zip(files)


async def provision_extension(
    *,
    project_id: str,
    run_id: str,
    prompt: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        raise ManagedExtensionError("Projet introuvable.")

    slug = project.github_branch
    github_repo = project.github_repo
    files = _extension_files(prompt, slug)

    await st.update_project(project_id, patch={"status": "building", "error_last": None})

    # Persist sources to GitHub branch (like vitrines)
    await push_vitrine_site_to_github(branch_slug=slug, files=files, settings=resolved, repo=github_repo)

    zip_bytes = build_extension_zip(files)
    await st.update_project(
        project_id,
        patch={
            "title": project.title or slug,
            "prompt_last": prompt,
            "status": "deployed",
            "url_production": None,
            "url_preview": None,
            "artifact_kind": "zip",
            "artifact_filename": f"{slug}.zip",
            "error_last": None,
        },
    )
    await st.finish_run(
        run_id,
        status="succeeded",
        artifacts={"artifact_kind": "zip", "artifact_bytes": len(zip_bytes)},
    )


async def update_extension(
    *,
    project_id: str,
    prompt: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> None:
    st = store
    run = await st.create_run(project_id, action="update")
    await provision_extension(
        project_id=project_id,
        run_id=run.id,
        prompt=prompt,
        settings=settings,
        store=store,
    )


async def hard_delete_extension(
    *,
    project_id: str,
    settings: Settings | None,
    store: ManagedProjectsStore,
) -> dict[str, Any]:
    return await hard_delete_managed_project(
        project_id=project_id,
        settings=settings,
        store=store,
        include_extension_zip=True,
        include_pipeline_projects=True,
    )

