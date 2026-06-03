"""
Manifeste de déploiement universel ExportAI — métadonnées projet + cibles.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from agents.coremind_agent import ProjectType


class DeployManifest(BaseModel):
    """Manifeste portable pour Cloudflare, Railway et GitHub."""

    version: str = "1"
    project_name: str
    project_type: str
    project_type_label: str
    provider: str = Field(description="cloudflare | railway | github")
    domain: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    files: list[str] = Field(default_factory=list)
    secondary_targets: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )


def slugify_project_name(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())
    slug = slug.strip("-") or "cyberforge-project"
    return slug[:max_len].rstrip("-")


def unique_deploy_slug(
    text: str,
    *,
    project_id: str | None = None,
    max_len: int = 48,
) -> str:
    """
    Slug Cloudflare/GitHub unique par génération (suffixe horodaté + entropie).

    Évite de réutiliser le même projet Pages quand le titre ou le nom saisi
    est identique entre deux runs.
    """
    base = slugify_project_name(text, max_len=max_len)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    uniq = re.sub(r"[^a-z0-9]", "", (project_id or secrets.token_hex(4)).lower())[:8]
    suffix = f"-{stamp}-{uniq}"
    max_base = max(8, max_len - len(suffix))
    trimmed = base[:max_base].rstrip("-") or "cf"
    return f"{trimmed}{suffix}"[:max_len].rstrip("-")


def select_export_provider(project_type: ProjectType, prompt: str) -> str:
    """Cloudflare pour démos HTML ; Railway pour backend / full-stack."""
    text = prompt.lower()
    if project_type == ProjectType.API_BACKEND:
        return "railway"
    if project_type in (
        ProjectType.APPLICATION_WEB,
        ProjectType.APPLICATION_DESKTOP,
        ProjectType.SAAS_DASHBOARD,
    ):
        if any(
            k in text
            for k in (
                "api",
                "backend",
                "fastapi",
                "fullstack",
                "full-stack",
                "postgresql",
                "microservice",
            )
        ):
            return "railway"
    return "cloudflare"


def build_deploy_manifest(
    *,
    project_name: str,
    project_type: ProjectType,
    project_type_label: str,
    provider: str,
    domain: str | None,
    env: dict[str, str],
    files: list[str],
    secondary_targets: list[str] | None = None,
) -> DeployManifest:
    return DeployManifest(
        project_name=project_name,
        project_type=project_type.value,
        project_type_label=project_type_label,
        provider=provider,
        domain=domain,
        env=env,
        files=sorted(set(files)),
        secondary_targets=secondary_targets or [],
    )
