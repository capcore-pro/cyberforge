"""
BuilderAI v2 — assemblage template-first et enrichissement LLM.

Tous les livrables HTML (vitrine, ecommerce, réservation, app web, desktop) :
DesignSystem → Template → Content → assemble + optimise. Pas de HTML from scratch.

real_app : génération React/TS via v0/DeepSeek (+ design_system).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from agents.architect_agent import ArchitectPlan
from agents.content_ai import fill_template_content
from agents.design_system_ai import format_design_system_for_prompt
from agents.demo_quality import code_result_from_html
from agents.template_first_service import must_use_template_first
from agents.template_first_policy import is_template_first_html_project
from agents.vitrine_policy import is_vitrine_html_project
from core.agent_contract import AgentContractError, AgentResult, require_ok
from tools.client_content_profile import (
    build_client_content_profile,
    sanitize_brand_name,
)
from tools.codegen_service import CodeGenerateResult
from tools.html_markdown import strip_markdown_code_fences
from tools.sector_template_catalog import (
    load_sector_template_html_for_plan,
    resolve_template_family_from_plan,
)

logger = logging.getLogger(__name__)

_ASSEMBLY_PROVIDER = "builder_assembly"
_ASSEMBLY_MODEL = "template-first-v2"

# real_app uniquement — le reste passe par assemblage template
_LLM_WITH_DESIGN_SYSTEM_CATEGORIES = frozenset()

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

_TAG_RE = re.compile(r"<(/?)([a-zA-Z][\w:-]*)([^>]*)>", re.DOTALL)


class HtmlOptimizeReport(BaseModel):
    valid: bool = True
    issues: list[str] = Field(default_factory=list)
    bytes_before: int = 0
    bytes_after: int = 0


class VitrineAssemblyResult(BaseModel):
    html: str
    generation: CodeGenerateResult
    template_id: str
    optimize_report: HtmlOptimizeReport


def uses_template_assembly(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None,
) -> bool:
    """
    Modes assemblés depuis un template sectoriel — pas de HTML LLM libre.
  """
    mode = (generation_mode or "client_demo").strip().lower()
    if mode == "real_app":
        return False
    if mode == "vitrine_next":
        return True
    if is_template_first_html_project(plan, generation_mode=generation_mode):
        return True
    if must_use_template_first(plan, generation_mode=generation_mode):
        return True
    if is_vitrine_html_project(plan, generation_mode=generation_mode):
        return True
    return False


def uses_llm_with_design_system(
    plan: ArchitectPlan,
    *,
    generation_mode: str | None,
) -> bool:
    """real_app — prompts enrichis v0/DeepSeek."""
    mode = (generation_mode or "").strip().lower()
    return mode == "real_app"


def append_design_system_to_prompt(
    prompt: str,
    design_system: Any | None,
) -> str:
    """Injecte la loi visuelle DesignSystemAI dans un prompt LLM."""
    block = format_design_system_for_prompt(design_system)
    if not block:
        return prompt
    if "LOI VISUELLE" in prompt:
        return prompt
    return f"{block}{prompt}"


def _html_without_embedded_code(html: str) -> str:
    """Retire script/style pour ne pas fausser la validation des balises."""
    out = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    return re.sub(r"<style[\s\S]*?</style>", "", out, flags=re.I)


def validate_html_tags(html: str) -> HtmlOptimizeReport:
    """Vérifications structurelles légères (balises, document)."""
    issues: list[str] = []
    stripped = html.strip()
    for_validation = _html_without_embedded_code(stripped)
    upper = stripped.upper()

    if not upper.startswith("<!DOCTYPE"):
        issues.append("DOCTYPE manquant")
    if len(re.findall(r"<html\b", stripped, re.I)) != 1:
        issues.append("balise <html> unique attendue")
    if len(re.findall(r"<head\b", stripped, re.I)) != 1:
        issues.append("balise <head> unique attendue")
    if len(re.findall(r"<body\b", stripped, re.I)) != 1:
        issues.append("balise <body> unique attendue")
    if "</HTML>" not in upper and "</html>" not in stripped:
        issues.append("fermeture </html> manquante")

    stack: list[str] = []
    for match in _TAG_RE.finditer(for_validation):
        closing, tag_name, _rest = match.groups()
        tag = tag_name.lower()
        if tag in _VOID_TAGS or tag.startswith("!") or tag == "doctype":
            continue
        if _rest.rstrip().endswith("/"):
            continue
        if closing:
            if not stack or stack[-1] != tag:
                issues.append(f"fermeture inattendue </{tag}>")
                if stack:
                    stack.pop()
            else:
                stack.pop()
        else:
            stack.append(tag)

    if len(stack) > 24:
        issues.append(f"trop de balises non fermées ({len(stack)})")
    elif stack:
        issues.append(f"balises non fermées : {', '.join(stack[:8])}")

    return HtmlOptimizeReport(
        valid=not issues,
        issues=issues,
        bytes_before=len(stripped.encode("utf-8")),
    )


def minify_html_light(html: str) -> str:
    """Minification légère — espaces entre balises, commentaires HTML."""
    out = re.sub(r"<!--[\s\S]*?-->", "", html)
    out = re.sub(r">\s+<", ">\n<", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def optimize_html(html: str, *, strict: bool = True) -> tuple[str, HtmlOptimizeReport]:
    """Minifie et valide ; lève si strict et structure invalide."""
    report = validate_html_tags(html)
    optimized = minify_html_light(html)
    report.bytes_after = len(optimized.encode("utf-8"))

    critical = [
        i
        for i in report.issues
        if any(
            k in i
            for k in ("DOCTYPE", "<html>", "<head>", "<body>", "fermeture </html>")
        )
    ]
    if strict and critical:
        raise AgentContractError(
            agent_id="builder_ai",
            code="invalid_html",
            message="HTML final invalide après assemblage.",
            detail="; ".join(critical),
        )
    return optimized, report


def assemble_template_html(
    *,
    template_html: str,
    client_name: str,
    sector: str,
    city: str = "",
    research_content: Any | None = None,
    design_system: Any | None = None,
    user_prompt: str = "",
    template_id: str = "vitrine_default",
    skip_content_fill: bool = False,
) -> AgentResult[VitrineAssemblyResult]:
    """
    Flux template-first BuilderAI v2 :
    1. ContentAI remplit les placeholders (sauf HTML déjà rempli)
    2. Optimisation + validation
    3. CodeGenerateResult pour le pipeline
    """
    if not (template_html or "").strip():
        return AgentResult.failure(
            agent_id="builder_ai",
            agent_name="BuilderAI",
            code="missing_template_html",
            message="template_html obligatoire pour l'assemblage.",
        )

    logger.info(
        "[BuilderAI] assemble_template_html | template_id=%s | skip_content_fill=%s | html_chars=%d",
        template_id,
        skip_content_fill,
        len(template_html),
    )
    raw = strip_markdown_code_fences(template_html.strip())
    has_placeholders = "{{" in raw and "}}" in raw

    try:
        if skip_content_fill and not has_placeholders:
            filled_html = raw
        else:
            content_result = fill_template_content(
                template_html=raw,
                client_name=client_name,
                sector=sector,
                city=city,
                research_content=research_content,
                design_system=design_system,
                user_prompt=user_prompt,
                template_id=template_id,
            )
            if not content_result.ok:
                return AgentResult.failure(
                    agent_id="builder_ai",
                    agent_name="BuilderAI",
                    code=content_result.error.code if content_result.error else "content_failed",
                    message=content_result.error.message if content_result.error else "ContentAI a échoué.",
                    detail=content_result.error.detail if content_result.error else None,
                )
            filled_html = require_ok(content_result).html

        final_html, report = optimize_html(
            strip_markdown_code_fences(filled_html),
            strict=True,
        )
        generation = code_result_from_html(
            final_html,
            summary=f"Assemblage template — {template_id} (BuilderAI v2)",
            model=_ASSEMBLY_MODEL,
            provider=_ASSEMBLY_PROVIDER,
        )
        return AgentResult.success(
            agent_id="builder_ai",
            agent_name="BuilderAI",
            data=VitrineAssemblyResult(
                html=final_html,
                generation=generation,
                template_id=template_id,
                optimize_report=report,
            ),
            meta={"template_id": template_id, "assembly": True},
        )
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id="builder_ai",
            agent_name="BuilderAI",
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )
    except Exception as exc:
        logger.exception("[BuilderAI] assemble_template_html")
        return AgentResult.failure(
            agent_id="builder_ai",
            agent_name="BuilderAI",
            code="assembly_failed",
            message="Échec assemblage template.",
            detail=str(exc),
        )


# Alias rétrocompatibilité tests / imports
assemble_vitrine_html = assemble_template_html


def resolve_assembly_inputs(
    *,
    user_prompt: str,
    plan: ArchitectPlan,
    research_content: Any | None,
    design_system: Any | None,
    template_html: str | None,
    sector_template: dict[str, Any] | None,
) -> tuple[str, str, str, str, str, bool]:
    """
    Déduit template HTML, secteur, ville, template_id, client.
    Retourne (html, client_name, sector, city, template_id, already_filled).
    """
    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_content,
        plan=plan,
    )
    client_name = profile.company_name or profile.display_name
    sector = profile.sector or plan.secteur or ""
    city = profile.city or ""

    if isinstance(research_content, dict):
        city = str(research_content.get("ville") or city)
        client_name = str(research_content.get("nom_entreprise") or client_name)

    from tools.client_content_profile import resolve_client_business_name

    client_name = resolve_client_business_name(
        client_name,
        sector=sector or plan.secteur or "",
        city=city,
        user_prompt=user_prompt,
    )
    sector_key = sector or plan.secteur or "commerce"
    expected_id, _expected_file, catalog_html = load_sector_template_html_for_plan(
        plan,
        sector_key,
        user_prompt,
    )
    template_id = expected_id
    html = (template_html or "").strip() or catalog_html
    already_filled = False
    family = resolve_template_family_from_plan(plan)

    if sector_template and isinstance(sector_template, dict):
        current_id = str(sector_template.get("template_id") or "")
        wrong_family = (
            family == "ecommerce"
            and (current_id.startswith("app_") or current_id.startswith("vitrine_"))
        ) or (
            family == "app"
            and current_id.startswith("ecommerce_")
        )
        if current_id and current_id != expected_id:
            logger.warning(
                "[BuilderAI] template_id pipeline=%s attendu=%s (family=%s) — correction catalogue",
                current_id,
                expected_id,
                family,
            )
            html = catalog_html
            template_id = expected_id
            already_filled = False
        elif wrong_family:
            logger.warning(
                "[BuilderAI] famille %s incompatible avec template_id=%s — rechargement %s",
                family,
                current_id,
                expected_id,
            )
            html = catalog_html
            template_id = expected_id
            already_filled = False
        else:
            template_id = current_id or expected_id
            if sector_template.get("content_filled") and sector_template.get("html"):
                html = strip_markdown_code_fences(str(sector_template["html"]))
                already_filled = "{{" not in html
            elif sector_template.get("html_raw"):
                html = strip_markdown_code_fences(str(sector_template["html_raw"]))
            elif sector_template.get("html"):
                html = strip_markdown_code_fences(str(sector_template["html"]))
            sector = str(sector_template.get("sector") or sector)

    if family == "ecommerce" and not template_id.startswith("ecommerce_"):
        logger.warning(
            "[BuilderAI] force ecommerce | template_id=%s → %s",
            template_id,
            expected_id,
        )
        template_id, _, html = load_sector_template_html_for_plan(
            plan, sector_key, user_prompt
        )
        already_filled = False

    html = strip_markdown_code_fences(html)
    return html, client_name, sector, city, template_id, already_filled
