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
from tools.vitrine.unsplash_resolver import resolve_vitrine_images

logger = logging.getLogger(__name__)

_TEXT_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".cjs",
    ".json",
    ".md",
    ".css",
    ".txt",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".gitignore",
}

_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
}


@dataclass(frozen=True)
class VitrineBuildResult:
    content: VitrineSiteContent
    output_dir: Path
    generation: CodeGenerateResult
    file_count: int
    images_resolved: int = 0


async def build_vitrine_site(
    prompt: str,
    *,
    project_type_label: str = "Site vitrine",
    branding: ClientBranding | None = None,
    output_dir: Path | None = None,
    settings: Settings | None = None,
    project_id: str | None = None,
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
            project_id=project_id,
        )
    except VitrineContentError:
        raise
    except Exception as exc:
        raise VitrineContentError(str(exc)) from exc

    content, image_stats = await resolve_vitrine_images(
        content,
        settings=resolved,
        project_id=project_id,
    )
    if image_stats.resolved:
        logger.info(
            "build_vitrine_site images | resolved=%s skipped=%s failed=%s",
            image_stats.resolved,
            image_stats.skipped,
            image_stats.failed,
        )

    try:
        scaffold = render_vitrine_scaffold(content, output_dir=output_dir)
    except ScaffoldRenderError:
        raise
    except Exception as exc:
        raise ScaffoldRenderError(str(exc)) from exc

    files: list[GeneratedFile] = []
    for rel in scaffold.files:
        if not _is_text_asset(rel):
            continue
        content_text = (scaffold.output_dir / rel).read_text(encoding="utf-8")
        files.append(GeneratedFile(path=rel, content=content_text))

    generation = CodeGenerateResult(
        summary=f"Site vitrine Next.js — {content.meta.businessName}",
        code="",
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
        images_resolved=image_stats.resolved,
    )


def _is_text_asset(relative_path: str) -> bool:
    lower = relative_path.lower()
    if "node_modules" in lower or "/.next/" in lower or lower.startswith(".next/"):
        return False
    suffix = Path(lower).suffix
    if suffix in _BINARY_EXTENSIONS:
        return False
    if suffix:
        return suffix in _TEXT_EXTENSIONS
    # fichiers sans extension (ex: .gitignore à la racine du template)
    return True
