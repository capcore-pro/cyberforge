"""Orchestration Phase 4.2b — contenu LLM + scaffold Next.js."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from config import Settings, get_settings
from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.vitrine.content_agent import VitrineContentAgent, VitrineContentError
from tools.vitrine.content_schema import ClientBranding, VitrineSiteContent
from tools.vitrine.scaffold_renderer import ScaffoldRenderError, render_vitrine_scaffold

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VitrineBuildResult:
    content: VitrineSiteContent
    output_dir: Path
    generation: CodeGenerateResult
    file_count: int


async def build_vitrine_site(
    prompt: str,
    *,
    project_type_label: str = "Site vitrine",
    branding: ClientBranding | None = None,
    output_dir: Path | None = None,
    settings: Settings | None = None,
) -> VitrineBuildResult:
    """
    Génère le JSON de contenu puis matérialise le projet Next.js dans output_dir.
    """
    resolved = settings or get_settings()
    agent = VitrineContentAgent(resolved)

    try:
        content = await agent.generate(
            prompt,
            project_type_label=project_type_label,
            branding=branding,
        )
    except VitrineContentError:
        raise
    except Exception as exc:
        raise VitrineContentError(str(exc)) from exc

    try:
        scaffold = render_vitrine_scaffold(content, output_dir=output_dir)
    except ScaffoldRenderError:
        raise
    except Exception as exc:
        raise ScaffoldRenderError(str(exc)) from exc

    site_json = scaffold.site_json_path.read_text(encoding="utf-8")
    site_rel = "content/site.json"
    files = [GeneratedFile(path=site_rel, content=site_json)]

    generation = CodeGenerateResult(
        summary=f"Site vitrine Next.js — {content.meta.businessName}",
        code=site_json,
        files=files,
        stack=["nextjs", "react", "typescript", "tailwind", "vitrine_next"],
        model="vitrine-content",
        provider="cyberforge",
    )

    logger.info(
        "build_vitrine_site OK | business=%s | dir=%s | files=%s",
        content.meta.businessName,
        scaffold.output_dir,
        len(files),
    )

    return VitrineBuildResult(
        content=content,
        output_dir=scaffold.output_dir,
        generation=generation,
        file_count=len(scaffold.files),
    )
