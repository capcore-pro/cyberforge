"""
Résolution du HTML à envoyer sur Cloudflare — pipeline uniquement, pas de cache Supabase.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.codegen_service import CodeGenerateResult
from tools.generation_sources import is_usable_preview_html
from tools.html_markdown import strip_markdown_code_fences

logger = logging.getLogger(__name__)

_SAAS_DASHBOARD_MARKERS = ("saas-shell", "cf-sidebar-nav", "cf-with-sidebar")


def _usable(html: str | None) -> bool:
    return bool(html and html.strip() and is_usable_preview_html(html.strip()))


def _normalize_index_html(html: str) -> str:
    """Nettoie fences markdown ; ne retire pas le gate (ajouté à l'upload Cloudflare)."""
    return strip_markdown_code_fences((html or "").strip())


def infer_template_id(
    *,
    explicit_template_id: str | None = None,
    sector_template: dict[str, Any] | None = None,
    generation: CodeGenerateResult | None = None,
) -> str:
    if explicit_template_id and str(explicit_template_id).strip():
        return str(explicit_template_id).strip()
    if isinstance(sector_template, dict):
        tid = str(sector_template.get("template_id") or "").strip()
        if tid:
            return tid
    if generation and generation.summary and "template" in generation.summary.lower():
        for part in generation.summary.split("—"):
            token = part.strip()
            if token.startswith("ecommerce_") or token.startswith("vitrine_"):
                return token
    return "unknown"


def looks_like_saas_dashboard(html: str) -> bool:
    low = html.lower()
    return any(m in low for m in _SAAS_DASHBOARD_MARKERS)


def resolve_export_html_for_upload(
    *,
    assembled_html: str | None = None,
    preview_html: str | None = None,
    generation: CodeGenerateResult | None = None,
    template_id: str | None = None,
    sector_template: dict[str, Any] | None = None,
    expect_sector_template: bool = False,
) -> tuple[str, str, str]:
    """
    Priorité stricte (jamais Supabase / fichier cache) :
    1. assembled_html — sortie assemble_template_html (pipeline)
    2. preview_html — state pipeline courant
    3. generation.files[index.html] puis generation.code (HTML uniquement)
    """
    tid = infer_template_id(
        explicit_template_id=template_id,
        sector_template=sector_template,
        generation=generation,
    )

    if _usable(assembled_html):
        html = _normalize_index_html(assembled_html)
        return html, "assembled_html", tid

    if _usable(preview_html):
        html = _normalize_index_html(preview_html)
        if expect_sector_template and looks_like_saas_dashboard(html):
            logger.warning(
                "[ExportAI] preview_html ressemble au dashboard SaaS — "
                "assembled_html absent (template_id=%s)",
                tid,
            )
        return html, "preview_html", tid

    if generation:
        for f in generation.files or []:
            path = (f.path or "").strip().lstrip("/").replace("\\", "/").lower()
            if path in ("index.html", "index.htm") and _usable(f.content):
                html = _normalize_index_html(f.content)
                return html, "generation.files", tid
        code = (generation.code or "").strip()
        if code and (
            code.lower().startswith("<!doctype")
            or "<html" in code[:800].lower()
        ):
            if _usable(code):
                html = _normalize_index_html(code)
                return html, "generation.code", tid

    return "", "none", tid


def resolve_pipeline_preview_html(
    *,
    assembled_html: str | None = None,
    preview_html: str | None = None,
    sector_template_html: str | None = None,
    generation: CodeGenerateResult | None = None,
    title: str = "Démo CyberForge",
    user_prompt: str = "",
) -> tuple[str | None, str | None]:
    """
    HTML d'aperçu final pour finalize / Supabase.
    Priorité : assembled_html > preview_html > sector_template > generation.
    Retourne (preview_html, assembled_html) identiques après préparation interne.
    """
    from agents.demo_quality import preview_html_from_generation
    from tools.demo_preview_gate import prepare_internal_app_preview_html

    assembled = _normalize_index_html(assembled_html or "") or ""
    preview = _normalize_index_html(preview_html or "") or ""
    sector = _normalize_index_html(sector_template_html or "") or ""

    canonical = assembled or preview or sector
    if not canonical and generation is not None:
        try:
            canonical = preview_html_from_generation(
                generation,
                title=title,
                user_prompt=user_prompt,
            )
        except ValueError:
            canonical = ""
        canonical = _normalize_index_html(canonical) or ""

    if not canonical:
        return None, None

    prepared = prepare_internal_app_preview_html(canonical)
    if not prepared.strip():
        return None, None
    return prepared, prepared


def force_finalize_preview_from_assembled(
    *,
    state_assembled_html: str | None,
    preview_html: str | None,
    assembled_html: str | None,
    sector_template_html: str | None,
    generation: CodeGenerateResult | None = None,
    title: str = "Démo CyberForge",
    user_prompt: str = "",
) -> tuple[str | None, str | None]:
    """
    Copie obligatoire assembled → preview_html (tous types de projets).
    Si assembled_html est dans le state, aucune exception : preview = assembled.
    """
    from tools.demo_preview_gate import prepare_internal_app_preview_html

    state_asm = _normalize_index_html(state_assembled_html or "") or ""
    if state_asm:
        prepared = prepare_internal_app_preview_html(state_asm) or state_asm
        return prepared, prepared

    resolved_asm = _normalize_index_html(assembled_html or "") or ""
    resolved_preview = _normalize_index_html(preview_html or "") or ""
    sector = _normalize_index_html(sector_template_html or "") or ""

    canonical = resolved_asm or resolved_preview or sector
    if not canonical and generation is not None:
        for f in generation.files or []:
            path = (f.path or "").strip().lstrip("/").lower()
            if path in ("index.html", "index.htm") and (f.content or "").strip():
                canonical = _normalize_index_html(f.content) or ""
                break
        if not canonical:
            code = (generation.code or "").strip()
            if code.lower().startswith("<!doctype") or "<html" in code[:800].lower():
                canonical = _normalize_index_html(code) or ""

    if not canonical:
        return None, None

    prepared = prepare_internal_app_preview_html(canonical) or canonical
    return prepared, prepared


def log_export_upload_source(
    *,
    source: str,
    template_id: str,
    html: str,
    extra: str = "",
) -> None:
    nbytes = len((html or "").encode("utf-8"))
    msg = (
        f"[ExportAI] upload source={source} template_id={template_id} bytes={nbytes}"
    )
    if extra:
        msg = f"{msg} {extra}"
    logger.info(msg)
