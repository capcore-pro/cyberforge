"""
Pipeline LangGraph complet — ArchitectAI → … → TestPilotAI → ExportAI → Finalisation.
ExportAI déploie sur Cloudflare Pages, Railway ou GitHub selon le type de projet.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import replace
from typing import Any, Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph

from agents.architect_agent import ArchitectAgent, ArchitectPlan
from agents.builder_agent import BuilderAgent, BuilderProvider
from agents.openhands_agent import OpenHandsAgent, openhands_eligible
from agents.playwright_agent import PlaywrightAgent
from agents.lighthouse_agent import LighthouseAgent
from agents.design_system_ai import (
    build_design_system,
    format_design_system_for_prompt,
)
from agents.content_ai import fill_template_content
from agents.template_ai import load_sector_template_raw
from agents.research_agent import (
    ResearchAgent,
    extract_research_context,
    format_research_brief_for_prompt,
)
from agents.stitch_ai import (
    StitchAgent,
    StitchResult,
    format_stitch_mockups_for_prompt,
)
from agents.auto_fix_agent import AutoFixAgent
from agents.bug_hunter_agent import BugHunterAgent, BugHuntReport
from agents.coremind_agent import (
    CoreMindAnalysis,
    CoreMindRunResult,
    DemoPipelineSummary,
    GenerationMetrics,
    ProjectType,
)
from agents.demo_quality import preview_html_from_generation
from agents.visionui_agent import VisionUIAgent
from agents.testpilot_agent import TestPilotAgent, testpilot_to_bug_report
from agents.export_agent import ExportAgent
from agents import database_ai
from agents import auth_ai
from agents import electron_ai
from config import Settings, get_settings
from cockpit_sync import flush_project_costs
from cost_tracker import set_architect_plan
from tools.codegen_service import CodeGenComplexity, CodeGenService
from tools.demo_pipeline import build_client_demo_document
from tools.demo_template_service import (
    DemoSeedData,
    DemoTemplateService,
    TEMPLATE_LABELS,
    align_seed_template,
)
from prompts import PERSONALIZED_CONTENT_DIRECTIVE
from tools.pricing import estimate_cost_usd
from tools.demo_template_service import TEMPLATE_MODEL, TEMPLATE_PROVIDER
from tools.toolbox_branding import (
    apply_toolbox_to_generation,
    apply_toolbox_vitrine_scaffold,
    build_toolbox_builder_context,
)
from tools.vitrine.build import VitrineContentError, build_vitrine_site
from tools.vitrine.scaffold_renderer import ScaffoldRenderError

logger = logging.getLogger(__name__)

MAX_AUTOFIX_LOOPS = 2
MAX_TESTPILOT_AUTOFIX_LOOPS = 1
MAX_PLAYWRIGHT_AUTOFIX_LOOPS = 1
MAX_LIGHTHOUSE_AUTOFIX_LOOPS = 1

# Modes avec routage direct CoreMindAI (saute BuilderAI).
# Vitrines : client_demo + vitrine_next passent par BuilderAI v2 (assemblage template).
DIRECT_COREMIND_MODES = frozenset({"real_app"})

# Ordre LangGraph nominal pour vitrine HTML (client_demo, vitrine_next).
# Étapes optionnelles : research (settings.research_enabled), stitch (stitch_enabled).
# Identifiants de nœuds LangGraph (≠ clés du state TypedDict)
NODE_DESIGN_SYSTEM = "design_system_ai"
NODE_DATABASE = "database_ai"
NODE_AUTH = "auth_ai"
NODE_ELECTRON = "electron_ai"

VITRINE_PIPELINE_ORDER: tuple[str, ...] = (
    "architect",
    "research",
    NODE_DESIGN_SYSTEM,
    "template_ai",
    "stitch",
    "content_ai",
    "builder",
    "visionui",
    "bughunter",
    "autofix",
    "testpilot",
    "playwright",
    "lighthouse",
    "export",
    "finalize",
)

VITRINE_OPTIONAL_STEPS: frozenset[str] = frozenset({"research", "stitch"})

PipelineEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

AGENT_LABELS: dict[str, str] = {
    "architect": "ArchitectAI",
    NODE_DESIGN_SYSTEM: "DesignSystemAI",
    "template_ai": "TemplateAI",
    "content_ai": "ContentAI",
    "research": "ResearchAI",
    "stitch": "StitchAI",
    "openhands": "OpenHands",
    "builder": "BuilderAI",
    "coremind": "CoreMindAI",
    "visionui": "VisionUI",
    "bughunter": "BugHunterAI",
    "autofix": "AutoFixAI",
    "testpilot": "TestPilotAI",
    "playwright": "Playwright",
    "lighthouse": "Lighthouse",
    "export": "ExportAI",
    "finalize": "Finalisation",
}

# Labels SSE spécifiques au mode "Vraie app"
REAL_APP_STEP_MESSAGES: dict[str, str] = {
    "coremind_start": "Génération app React/TypeScript…",
    "export_start": "Déploiement application React (Railway / Vercel)…",
}


class PipelineState(TypedDict, total=False):
    prompt: str
    inspiration_brief: str | None
    project_id: str | None
    project_type: str | None
    project_type_hint: ProjectType | None
    # "client_demo" (défaut) → pipeline HTML premium ; "real_app" → React/Next.js
    generation_mode: str | None
    openhands_enabled: bool | None
    playwright_enabled: bool | None
    lighthouse_enabled: bool | None
    research_enabled: bool | None
    stitch_enabled: bool | None
    architect_plan: ArchitectPlan | None
    design_system: Any
    sector_template: Any
    analysis: CoreMindAnalysis | None
    builder_provider: str | None
    builder_fallback: bool
    openhands_fallback: bool | None
    generation: Any
    assembled_html: str | None
    preview_html: str | None
    vision_screenshot_url: str | None
    vision_preview_source: str | None
    bug_report: BugHuntReport | None
    fix_loops: int
    autofix_attempts: int
    testpilot_report: Any
    testpilot_refix_loops: int
    playwright_report: Any
    playwright_autofix_loops: int
    lighthouse_report: Any
    lighthouse_autofix_loops: int
    research_brief: Any
    stitch_result: Any
    validation_status: str | None
    personal_project: bool | None
    pages_project_slug: str | None
    project_title: str | None
    export_result: Any
    extension_files: dict[str, str] | None
    artifact_download_url: str | None
    result: CoreMindRunResult | None
    error: str | None
    database_schema: Any
    auth_schema: Any
    electron_files: Any


def is_vitrine_generation_mode(state: PipelineState) -> bool:
    """True pour les modes vitrine HTML assemblée (pas real_app)."""
    mode = (state.get("generation_mode") or "client_demo").strip().lower()
    return mode in ("client_demo", "vitrine_next")


async def _emit(
    callback: PipelineEventCallback | None,
    event: dict[str, Any],
) -> None:
    if callback is None:
        return
    maybe = callback(event)
    if maybe is not None:
        await maybe


async def _step(
    callback: PipelineEventCallback | None,
    agent: str,
    phase: str,
    message: str = "",
    **extra: Any,
) -> None:
    payload: dict[str, Any] = {
        "type": f"step_{phase}",
        "agent": agent,
        "agent_name": AGENT_LABELS.get(agent, agent),
        "message": message,
        **extra,
    }
    await _emit(callback, payload)


def _configurable(config: dict[str, Any] | None) -> dict[str, Any]:
    if not config:
        return {}
    return config.get("configurable") or {}


def _settings_from_config(config: dict[str, Any] | None) -> Settings:
    cfg = _configurable(config)
    if "settings" in cfg:
        return cfg["settings"]
    return get_settings()


def _callback_from_config(config: dict[str, Any] | None) -> PipelineEventCallback | None:
    return _configurable(config).get("on_event")


def _architect_input_prompt(state: PipelineState) -> str:
    """Fusionne le brief d'inspiration Firecrawl et le prompt utilisateur."""
    base = (state.get("prompt") or "").strip()
    brief = (state.get("inspiration_brief") or "").strip()
    if not brief:
        return base
    if not base:
        return brief
    return (
        "## Brief d'inspiration (site source analysé)\n\n"
        f"{brief}\n\n"
        "## Prompt utilisateur\n\n"
        f"{base}"
    )


async def architect_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    await _step(cb, "architect", "start", "Analyse du prompt et choix du template…")
    settings = _settings_from_config(config)
    agent = ArchitectAgent(settings)
    plan, coremind_analysis = await agent.plan_with_analysis(
        _architect_input_prompt(state),
        project_type_hint=state.get("project_type_hint"),
        generation_mode=state.get("generation_mode"),
    )
    await _step(
        cb,
        "architect",
        "done",
        (
            f"{plan.project_type_label} · template {plan.template_label} · "
            f"{plan.complexity_label} ({plan.complexity_score}/10) · "
            f"marché {plan.market_price_min}–{plan.market_price_max} €"
        ),
        template=plan.template,
        project_type=plan.project_type.value,
        used_llm=plan.used_llm,
        complexity_score=plan.complexity_score,
        complexity_label=plan.complexity_label,
        market_price_min=plan.market_price_min,
        market_price_max=plan.market_price_max,
        suggested_price_min=plan.suggested_price_min,
        suggested_price_max=plan.suggested_price_max,
        pricing_category=plan.pricing_category,
    )
    project_id = state.get("project_id")
    if project_id:
        set_architect_plan(str(project_id), plan)
    mode = (state.get("generation_mode") or "client_demo").strip().lower()
    return {
        "architect_plan": plan,
        "analysis": coremind_analysis,
        "project_type": "vitrine_next" if mode == "vitrine_next" else plan.project_type.value,
    }


def _should_run_database_ai(state: PipelineState) -> bool:
    """
    Exécute DatabaseAI après ArchitectAI sauf:
    - vitrine_next (mode Next.js)
    - extension_navigateur
    """
    pt = (state.get("project_type") or "").strip().lower()
    return pt not in ("vitrine_next", "extension_navigateur")


async def database_ai_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    await _step(cb, NODE_DATABASE, "start", "Génération du schéma Supabase…")
    plan = state.get("architect_plan")
    if not plan:
        await _step(cb, NODE_DATABASE, "done", "Plan ArchitectAI manquant — étape ignorée.", ok=True)
        return {}

    project_type = (
        plan.project_type.value
        if hasattr(plan.project_type, "value")
        else str(plan.project_type)
    )
    try:
        schema = await database_ai.run(
            project_description=state.get("prompt") or "",
            project_type=project_type,
            design_system=state.get("design_system")
            if isinstance(state.get("design_system"), dict)
            else {},
        )
    except Exception as exc:
        logger.exception("DatabaseAI erreur non bloquante: %s", exc)
        await _step(
            cb,
            NODE_DATABASE,
            "done",
            "DatabaseAI indisponible — suite du pipeline.",
            ok=True,
            skipped=True,
        )
        return {}
    await _step(
        cb,
        NODE_DATABASE,
        "done",
        str(schema.get("summary") or "Schéma Supabase généré."),
        ok=True,
    )
    return {"database_schema": schema}


def _should_run_auth_ai(state: PipelineState) -> bool:
    pt = (state.get("project_type") or "").strip().lower()
    desc = (state.get("prompt") or "").strip()
    return auth_ai.detect_auth_type(desc, pt) != "public"


async def auth_ai_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    await _step(cb, NODE_AUTH, "start", "Génération du schéma Auth/RLS…")

    try:
        schema = await auth_ai.run(
            project_description=state.get("prompt") or "",
            project_type=str(state.get("project_type") or ""),
            database_schema=state.get("database_schema") if isinstance(state.get("database_schema"), dict) else {},
        )
    except Exception as exc:
        logger.exception("AuthAI erreur non bloquante: %s", exc)
        await _step(
            cb,
            NODE_AUTH,
            "done",
            "AuthAI indisponible — suite du pipeline.",
            ok=True,
            skipped=True,
        )
        return {}

    # Skip si public (contrat demandé)
    if (schema.get("auth_type") or "").strip().lower() == "public":
        await _step(cb, NODE_AUTH, "done", "Auth public — étape ignorée.", ok=True, skipped=True)
        return {}

    await _step(
        cb,
        NODE_AUTH,
        "done",
        str(schema.get("summary") or "Schéma Auth/RLS généré."),
        ok=True,
    )
    return {"auth_schema": schema}


def _should_run_electron_ai(state: PipelineState) -> bool:
    return (state.get("project_type") or "").strip().lower() == "application_desktop"


async def electron_ai_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    await _step(cb, NODE_ELECTRON, "start", "Génération du projet Electron (Windows)…")
    try:
        result = await electron_ai.run(
            project_description=state.get("prompt") or "",
            assembled_html=str(state.get("assembled_html") or state.get("preview_html") or ""),
            database_schema=state.get("database_schema") if isinstance(state.get("database_schema"), dict) else {},
        )
    except Exception as exc:
        logger.exception("ElectronAI erreur non bloquante: %s", exc)
        await _step(
            cb,
            NODE_ELECTRON,
            "done",
            "ElectronAI indisponible — suite du pipeline.",
            ok=True,
            skipped=True,
        )
        return {}

    await _step(
        cb,
        NODE_ELECTRON,
        "done",
        str(result.get("summary") or "Fichiers Electron générés."),
        ok=True,
    )
    return {"electron_files": result}


def _generation_user_prompt(state: PipelineState) -> str:
    """Prompt enrichi : ResearchAI + maquettes StitchAI + prompt utilisateur."""
    from tools.client_content_profile import (
        build_client_content_profile,
        format_literal_client_directive,
    )

    base = (state.get("prompt") or "").strip()
    design_block = format_design_system_for_prompt(state.get("design_system"))
    research_block = format_research_brief_for_prompt(state.get("research_brief"))
    stitch_block = format_stitch_mockups_for_prompt(state.get("stitch_result"))
    literal_block = format_literal_client_directive(
        build_client_content_profile(
            user_prompt=base,
            research_brief=state.get("research_brief"),
            plan=state.get("architect_plan"),
        ),
        user_prompt=base,
    )
    prefix = f"{design_block}{research_block}{stitch_block}{literal_block}"
    if prefix:
        return f"{prefix}{base}"
    return base


async def design_system_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """DesignSystemAI — loi visuelle après Research, avant Template / Content."""
    cb = _callback_from_config(config)
    await _step(cb, NODE_DESIGN_SYSTEM, "start", "Génération du design system…")
    plan = state.get("architect_plan")
    if not plan:
        return {
            "error": "Plan architecte manquant pour DesignSystemAI.",
        }

    from tools.client_content_profile import build_client_content_profile

    base_prompt = (state.get("prompt") or "").strip()
    profile = build_client_content_profile(
        user_prompt=base_prompt,
        research_brief=state.get("research_brief"),
        plan=plan,
    )
    sector = (
        (profile.sector or "").strip()
        or (plan.secteur or "").strip()
        or detect_sector_from_prompt_for_design(base_prompt, plan)
    )
    client_name = profile.company_name or profile.display_name

    result = build_design_system(
        sector=sector,
        client_name=client_name,
        palette_preference=plan.palette,
        project_type=plan.project_type,
        user_prompt=base_prompt,
    )
    if not result.ok or result.data is None:
        err = result.error
        msg = err.message if err else "Design system incomplet."
        await _step(cb, NODE_DESIGN_SYSTEM, "error", msg)
        return {"error": f"DesignSystemAI : {msg}"}

    doc = result.data
    meta = result.meta or {}
    await _step(
        cb,
        NODE_DESIGN_SYSTEM,
        "done",
        f"Palette {doc.colors.primary} · {doc.fonts.heading} / {doc.fonts.body}",
        sector=meta.get("sector") or sector,
        palette_source=meta.get("palette_source"),
    )
    return {"design_system": doc.to_contract_dict()}


async def template_ai_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """TemplateAI — charge le HTML sectoriel de base (loi visuelle déjà fixée)."""
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    if not plan:
        return {"error": "Plan architecte manquant pour TemplateAI."}

    await _step(cb, "template_ai", "start", "Chargement du template sectoriel…")

    from tools.client_content_profile import build_client_content_profile

    base_prompt = (state.get("prompt") or "").strip()
    profile = build_client_content_profile(
        user_prompt=base_prompt,
        research_brief=state.get("research_brief"),
        plan=plan,
    )
    sector = (
        (profile.sector or "").strip()
        or (plan.secteur or "").strip()
        or detect_sector_from_prompt_for_design(base_prompt, plan)
    )

    pt_value = (
        plan.project_type.value
        if hasattr(plan.project_type, "value")
        else str(plan.project_type)
    )
    pricing_cat = (getattr(plan, "pricing_category", None) or "").strip().lower()
    logger.info(
        "[TemplateAI] entrée | project_type=%s | pricing_category=%s | sector=%s | prompt_len=%d",
        pt_value,
        pricing_cat or "?",
        sector,
        len(base_prompt),
    )

    result = load_sector_template_raw(
        sector=sector,
        user_prompt=base_prompt,
        plan=plan,
    )
    if not result.ok or result.data is None:
        err = result.error
        msg = err.message if err else "Template sectoriel indisponible."
        await _step(cb, "template_ai", "error", msg)
        return {"error": f"TemplateAI : {msg}"}

    data = result.data
    logger.info(
        "[TemplateAI] choix catalogue | project_type=%s | pricing_category=%s → template_id=%s (%s)",
        pt_value,
        pricing_cat or "?",
        data.template_id,
        data.template_file,
    )
    await _step(
        cb,
        "template_ai",
        "done",
        f"Template {data.template_id} — {data.sector}",
        template_id=data.template_id,
        template_file=data.template_file,
    )
    return {
        "sector_template": {
            "template_id": data.template_id,
            "template_file": data.template_file,
            "sector": data.sector,
            "visual_family": data.visual_family,
            "html_raw": data.html,
            "html": data.html,
        },
    }


async def content_ai_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """ContentAI — contenu client réel dans le template sectoriel."""
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    sector_tpl = state.get("sector_template")
    if not plan or not isinstance(sector_tpl, dict):
        return {"error": "Template sectoriel manquant pour ContentAI."}

    template_html = sector_tpl.get("html_raw") or sector_tpl.get("html") or ""
    template_id = str(sector_tpl.get("template_id") or "vitrine_default")

    await _step(cb, "content_ai", "start", "Rédaction du contenu client…")

    from tools.client_content_profile import build_client_content_profile

    base_prompt = (state.get("prompt") or "").strip()
    profile = build_client_content_profile(
        user_prompt=base_prompt,
        research_brief=state.get("research_brief"),
        plan=plan,
    )
    research = state.get("research_brief")
    sector = str(sector_tpl.get("sector") or profile.sector or "")
    client_name = profile.company_name or profile.display_name
    city = profile.city or ""
    if isinstance(research, dict) and research.get("ville"):
        city = str(research.get("ville") or city)
    if isinstance(research, dict) and research.get("nom_entreprise"):
        client_name = str(research.get("nom_entreprise") or client_name)

    result = fill_template_content(
        template_html=template_html,
        client_name=client_name,
        sector=sector,
        city=city,
        research_content=research,
        design_system=state.get("design_system"),
        user_prompt=base_prompt,
        template_id=template_id,
    )
    if not result.ok or result.data is None:
        err = result.error
        msg = err.message if err else "Contenu client incomplet."
        await _step(cb, "content_ai", "error", msg)
        return {"error": f"ContentAI : {msg}"}

    data = result.data
    from tools.export_html_resolve import resolve_pipeline_preview_html

    filled_preview, filled_assembled = resolve_pipeline_preview_html(
        assembled_html=data.html,
        preview_html=data.html,
        sector_template_html=data.html,
        title=plan.project_type_label if plan else "Démo CyberForge",
        user_prompt=base_prompt,
    )
    await _step(
        cb,
        "content_ai",
        "done",
        f"Contenu {data.client_name} — {template_id}",
        client_name=data.client_name,
    )
    out: dict[str, Any] = {
        "sector_template": {
            **sector_tpl,
            "html": data.html,
            "content_filled": True,
            "keywords_used": data.keywords_used,
        },
    }
    if filled_preview:
        out["preview_html"] = filled_preview
        out["assembled_html"] = filled_assembled
    return out


def _sector_template_html_from_state(state: PipelineState) -> str | None:
    raw = state.get("sector_template")
    if isinstance(raw, dict):
        html = raw.get("html")
        if isinstance(html, str) and html.strip():
            return html
    return None


def detect_sector_from_prompt_for_design(prompt: str, plan: ArchitectPlan) -> str:
    from tools.toolbox_sectors import detect_sector_from_prompt

    return detect_sector_from_prompt(
        prompt,
        project_type=plan.project_type,
        pricing_category=getattr(plan, "pricing_category", None),
    )


def _route_after_architect(state: PipelineState) -> str:
    """ResearchAI (si activé) juste après Architect — avant loi visuelle."""
    if state.get("error"):
        return "finalize"
    if _should_run_database_ai(state):
        return NODE_DATABASE
    if _research_requested(state):
        return "research"
    return NODE_DESIGN_SYSTEM


def _route_after_database_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _should_run_auth_ai(state):
        return NODE_AUTH
    if _research_requested(state):
        return "research"
    return NODE_DESIGN_SYSTEM


def _route_after_auth_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _should_run_electron_ai(state):
        return NODE_ELECTRON
    if _research_requested(state):
        return "research"
    return NODE_DESIGN_SYSTEM


def _route_after_electron_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _research_requested(state):
        return "research"
    return NODE_DESIGN_SYSTEM


def _route_after_research(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return NODE_DESIGN_SYSTEM


def _is_extension_pipeline(state: PipelineState) -> bool:
    plan = state.get("architect_plan")
    if not plan:
        return False
    from tools.extension_pipeline import is_extension_project_type

    return is_extension_project_type(plan)


def _route_after_design_system(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _is_extension_pipeline(state):
        return "extension_build"
    return "template_ai"


async def extension_build_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extension Chrome MV3 — popup + manifest + scripts (pas template-first)."""
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    if not plan:
        return {"error": "Plan Architect manquant pour l'extension."}

    await _step(cb, "extension_build", "start", "Génération extension Chrome MV3…")

    from tools.codegen_service import CodeGenerateResult, GeneratedFile
    from tools.extension_pipeline import (
        _EXTENSION_MODEL,
        _EXTENSION_PROVIDER,
        build_extension_files,
        prepare_extension_preview_html,
    )

    prompt = state.get("prompt") or ""
    primary = "#4f46e5"
    ds = state.get("design_system")
    if isinstance(ds, dict):
        primary = str(ds.get("PRIMARY_COLOR") or ds.get("primary") or primary)

    slug = (state.get("pages_project_slug") or state.get("project_id") or "").strip()
    if not slug:
        slug = None

    try:
        files = build_extension_files(prompt, slug=slug, primary_color=primary)
    except Exception as exc:
        logger.exception("[extension_build] échec")
        await _step(cb, "extension_build", "error", str(exc))
        return {"error": f"Extension : {exc}"}

    popup_html = files.get("popup.html", "")
    preview_html = prepare_extension_preview_html(
        popup_html,
        popup_js=files.get("popup.js"),
        prompt=prompt,
    )
    gen_files = [
        GeneratedFile(path=path, content=content)
        for path, content in sorted(files.items())
    ]
    generation = CodeGenerateResult(
        summary=f"Extension Chrome MV3 — {len(files)} fichiers",
        code=popup_html,
        files=gen_files,
        stack=["chrome-extension", "manifest-v3"],
        model=_EXTENSION_MODEL,
        provider=_EXTENSION_PROVIDER,
    )

    await _step(
        cb,
        "extension_build",
        "done",
        f"Extension MV3 — popup {len(popup_html)} car.",
        preview_html=preview_html,
    )
    return {
        "generation": generation,
        "assembled_html": popup_html,
        "preview_html": preview_html,
        "extension_files": files,
        "builder_fallback": False,
    }


def _route_after_template_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _stitch_requested(state):
        return "stitch"
    return "content_ai"


def _route_after_content_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return _route_post_stitch(state)


def _research_requested(state: PipelineState) -> bool:
    if state.get("research_enabled") is False:
        return False
    return get_settings().research_enabled


def _stitch_requested(state: PipelineState) -> bool:
    if state.get("stitch_enabled") is False:
        return False
    return get_settings().stitch_enabled


def _route_post_stitch(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    plan = state.get("architect_plan")
    if plan and _openhands_requested(state):
        return "openhands"
    mode = (state.get("generation_mode") or "client_demo").strip()
    if mode in DIRECT_COREMIND_MODES:
        return "coremind"
    return "builder"


async def stitch_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    if not plan:
        return {"error": "État pipeline incomplet (architect_plan manquant pour StitchAI)."}

    ctx = extract_research_context(state.get("prompt") or "", plan=plan)
    await _step(
        cb,
        "stitch",
        "start",
        f"Maquettes Stitch — {ctx.get('nom_entreprise') or plan.project_type_label}…",
    )
    settings = _settings_from_config(config)
    agent = StitchAgent(settings)

    async def on_progress(message: str) -> None:
        await _step(cb, "stitch", "start", message)

    try:
        result = await agent.generate_mockups(
            architect_plan=plan,
            generation_mode=state.get("generation_mode"),
            research_brief=state.get("research_brief"),
            user_prompt=state.get("prompt") or "",
            design_system=state.get("design_system"),
            settings=settings,
            on_progress=on_progress,
        )
    except Exception as exc:
        logger.exception("StitchAI — erreur non bloquante, suite du pipeline")
        result = StitchResult(
            success=False,
            mockups=[],
            error=f"timeout ({exc!s})"[:120],
        )

    if result.skipped:
        await _step(
            cb,
            "stitch",
            "done",
            result.skip_reason or "StitchAI ignoré.",
            ok=True,
            stitch_skipped=True,
        )
        return {"stitch_result": result}

    if not result.success or not result.mockups:
        msg = result.error or "Maquettes Stitch non générées — suite sans référence visuelle."
        if (result.error or "").strip().lower() == "timeout":
            msg = "StitchAI ignoré (délai 30 s) — suite sans maquette."
        await _step(
            cb,
            "stitch",
            "done",
            msg,
            ok=True,
            stitch_skipped=True,
        )
        return {"stitch_result": result}

    await _step(
        cb,
        "stitch",
        "done",
        f"{len(result.mockups)} maquette(s) Stitch prête(s).",
        ok=True,
        stitch_project_id=result.project_id,
        stitch_mockup_count=len(result.mockups),
        stitch_mockups=[m.model_dump() for m in result.mockups],
    )
    return {"stitch_result": result}


def _route_after_stitch(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return "content_ai"


async def research_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    if not plan:
        return {"error": "État pipeline incomplet (architect_plan manquant pour ResearchAI)."}

    ctx = extract_research_context(state.get("prompt") or "", plan=plan)
    await _step(
        cb,
        "research",
        "start",
        f"Recherche contenu — {ctx['secteur'] or 'secteur'} "
        f"({ctx['nom_entreprise'] or 'projet'})…",
    )
    settings = _settings_from_config(config)
    agent = ResearchAgent(settings)
    brief = await agent.research(
        secteur=ctx["secteur"],
        nom_entreprise=ctx["nom_entreprise"],
        ville=ctx["ville"],
        type_projet=ctx["type_projet"],
        prompt=state.get("prompt") or "",
        settings=settings,
    )

    if brief.skipped or not brief.enriched:
        await _step(
            cb,
            "research",
            "done",
            brief.skip_reason or "Recherche ignorée — génération sans brief externe.",
            ok=True,
            research_skipped=True,
        )
        return {"research_brief": brief}

    await _step(
        cb,
        "research",
        "done",
        f"Brief enrichi — {len(brief.tendances)} tendance(s), "
        f"{len(brief.concurrents)} concurrent(s), "
        f"{len(brief.mots_cles)} mot(s)-clé(s).",
        ok=True,
        research_skipped=False,
    )
    return {"research_brief": brief}


def _openhands_requested(state: PipelineState) -> bool:
    plan = state.get("architect_plan")
    if not plan:
        return False
    enabled = state.get("openhands_enabled")
    if enabled is False:
        return False
    settings = get_settings()
    if not settings.openhands_enabled:
        return False
    if not OpenHandsAgent(settings).is_configured():
        return False
    return openhands_eligible(
        plan=plan,
        generation_mode=state.get("generation_mode"),
        enabled=True,
        threshold=settings.openhands_complexity_threshold,
    )


async def openhands_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    analysis = state.get("analysis")
    if not plan or not analysis:
        return {"error": "État pipeline incomplet (architect_plan manquant pour OpenHands)."}

    await _step(
        cb,
        "openhands",
        "start",
        f"Génération avancée OpenHands (complexité {plan.complexity_score}/10)…",
    )
    settings = _settings_from_config(config)
    agent = OpenHandsAgent(settings)
    result = await agent.build(
        _generation_user_prompt(state),
        plan=plan,
        analysis=analysis,
        settings=settings,
        project_id=state.get("project_id"),
    )

    if result.fallback_to_coremind:
        await _step(
            cb,
            "openhands",
            "done",
            "OpenHands indisponible — reprise par CoreMindAI.",
            provider=result.provider,
            fallback=True,
        )
        return {
            "builder_provider": result.provider,
            "openhands_fallback": True,
            "builder_fallback": True,
        }

    await _step(
        cb,
        "openhands",
        "done",
        f"Génération OpenHands réussie ({result.provider}).",
        provider=result.provider,
        fallback=False,
    )
    return {
        "builder_provider": result.provider,
        "openhands_fallback": False,
        "builder_fallback": False,
        "generation": result.generation,
        "preview_html": result.preview_html,
    }


def _route_after_openhands(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if state.get("builder_fallback", True):
        return "coremind"
    if state.get("generation"):
        return "visionui"
    return "coremind"


async def builder_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    analysis = state.get("analysis")
    if not plan or not analysis:
        return {"error": "État pipeline incomplet (architect_plan manquant pour BuilderAI)."}

    await _step(cb, "builder", "start", "Assemblage template ou génération v0/DeepSeek…")
    settings = _settings_from_config(config)
    agent = BuilderAgent(settings)
    user_prompt = _generation_user_prompt(state)
    from tools.client_content_profile import (
        build_client_content_profile,
        log_client_content_context,
    )

    client_profile = build_client_content_profile(
        user_prompt=state.get("prompt") or "",
        research_brief=state.get("research_brief"),
        plan=plan,
    )
    log_client_content_context(client_profile, prefix="BuilderAI")
    logger.info(
        "[BuilderAI] pipeline | research_in_prompt=%s | prompt_chars=%d | brief_type=%s",
        "## Brief recherche" in user_prompt,
        len(user_prompt),
        type(state.get("research_brief")).__name__,
    )
    sector_tpl = state.get("sector_template")
    sector_tid = (
        str(sector_tpl.get("template_id"))
        if isinstance(sector_tpl, dict) and sector_tpl.get("template_id")
        else "?"
    )
    logger.info(
        "[BuilderAI] pipeline | project_type=%s | pricing_category=%s | sector_template_id=%s | assemble_attendu=%s",
        plan.project_type.value,
        getattr(plan, "pricing_category", ""),
        sector_tid,
        True,
    )

    result = await agent.build(
        user_prompt,
        plan=plan,
        analysis=analysis,
        settings=settings,
        project_id=state.get("project_id"),
        design_system=state.get("design_system"),
        sector_template_html=_sector_template_html_from_state(state),
        sector_template=sector_tpl,
        research_brief=state.get("research_brief"),
        generation_mode=state.get("generation_mode"),
    )
    if result.decision.provider == BuilderProvider.ASSEMBLY:
        provider_label = "Assemblage template"
    elif result.decision.provider == BuilderProvider.V0:
        provider_label = "v0"
    else:
        provider_label = "DeepSeek"

    if result.fallback_to_coremind:
        logger.warning(
            "[BuilderAI] fallback CoreMind | provider=%s | sector_template_id=%s — "
            "risque template premium dashboard si pas de reprise template-first",
            result.decision.provider.value,
            sector_tid,
        )
        await _step(
            cb,
            "builder",
            "done",
            f"{provider_label} indisponible — reprise par CoreMindAI.",
            provider=result.decision.provider.value,
            fallback=True,
        )
        return {
            "builder_provider": result.decision.provider.value,
            "builder_fallback": True,
        }

    if result.generation:
        logger.info(
            "[BuilderAI] assemble_template_html OK | preview_chars=%d | model=%s",
            len(result.preview_html or result.generation.code or ""),
            getattr(result.generation, "model", "?"),
        )

    from tools.demo_preview_gate import prepare_internal_app_preview_html

    builder_preview = result.preview_html
    if builder_preview:
        builder_preview = prepare_internal_app_preview_html(str(builder_preview))

    await _step(
        cb,
        "builder",
        "done",
        f"Génération via {provider_label} réussie.",
        provider=result.decision.provider.value,
        fallback=False,
        preview_html=builder_preview,
    )
    return {
        "builder_provider": result.decision.provider.value,
        "builder_fallback": False,
        "generation": result.generation,
        "assembled_html": builder_preview,
        "preview_html": builder_preview,
    }


def _block_coremind_builder_fallback(state: PipelineState) -> bool:
    """E-commerce / template sectoriel : ne jamais envoyer vers CoreMind dashboard."""
    plan = state.get("architect_plan")
    if not plan:
        return False
    from agents.builder_agent import must_force_sector_template_assembly

    return must_force_sector_template_assembly(
        plan,
        sector_template_html=_sector_template_html_from_state(state),
        sector_template=state.get("sector_template"),
    )


def _route_after_builder(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if state.get("builder_fallback", True):
        if _block_coremind_builder_fallback(state):
            logger.error(
                "[BuilderAI] fallback CoreMind BLOQUÉ — template sectoriel requis "
                "(category=%s)",
                getattr(state.get("architect_plan"), "pricing_category", "?"),
            )
            if state.get("generation"):
                return "visionui"
            return "finalize"
        return "coremind"
    if state.get("generation"):
        return "visionui"
    return "coremind"


def _inject_package_json(
    generation: Any,
    project_label: str,
    *,
    plan: ArchitectPlan | None = None,
) -> Any:
    """
    Ajoute package.json + src/main.tsx + index.html si absents de la génération
    pour produire un projet React/Vite déployable sur Railway ou Vercel.
    """
    import json as _json
    from tools.codegen_service import CodeGenerateResult, GeneratedFile

    if not isinstance(generation, CodeGenerateResult):
        return generation

    existing_paths = {f.path for f in generation.files}
    extra: list[GeneratedFile] = []

    if "package.json" not in existing_paths:
        slug = re.sub(r"[^a-z0-9-]", "-", project_label.lower().strip())[:40] or "vraie-app"
        pkg = {
            "name": slug,
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview",
                "start": "vite",
            },
            "dependencies": {
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
            },
            "devDependencies": {
                "@types/react": "^18.3.1",
                "@types/react-dom": "^18.3.1",
                "@vitejs/plugin-react": "^4.3.1",
                "typescript": "^5.5.3",
                "vite": "^5.4.1",
            },
        }
        pkg_content = _json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"
        if plan and plan.palette:
            from tools.toolbox_branding import _merge_package_json

            pkg_content = _merge_package_json(pkg_content, plan)
        extra.append(GeneratedFile(path="package.json", content=pkg_content))

    if "index.html" not in existing_paths and "src/main.tsx" not in existing_paths:
        extra.append(GeneratedFile(
            path="index.html",
            content=(
                '<!DOCTYPE html>\n<html lang="fr">\n  <head>\n'
                '    <meta charset="UTF-8" />\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                f'    <title>{project_label}</title>\n'
                '  </head>\n  <body>\n    <div id="root"></div>\n'
                '    <script type="module" src="/src/main.tsx"></script>\n'
                '  </body>\n</html>'
            ),
        ))
        extra.append(GeneratedFile(
            path="src/main.tsx",
            content=(
                'import React from "react";\n'
                'import ReactDOM from "react-dom/client";\n'
                'import App from "./App";\n\n'
                'ReactDOM.createRoot(document.getElementById("root")!).render(\n'
                '  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n'
            ),
        ))

    if plan and plan.palette and "package.json" in existing_paths:
        from tools.toolbox_branding import _merge_package_json

        updated_files: list[GeneratedFile] = []
        for f in generation.files:
            if f.path == "package.json":
                updated_files.append(
                    GeneratedFile(
                        path=f.path,
                        content=_merge_package_json(f.content, plan),
                    )
                )
            else:
                updated_files.append(f)
        generation = CodeGenerateResult(
            summary=generation.summary,
            code=generation.code,
            files=updated_files,
            stack=list(generation.stack),
            model=generation.model,
            provider=generation.provider,
            demo_seed=generation.demo_seed,
        )

    if not extra:
        return generation

    new_stack = list(generation.stack)
    for tag in ("react", "typescript", "vite"):
        if tag not in new_stack:
            new_stack.append(tag)

    return CodeGenerateResult(
        summary=generation.summary,
        code=generation.code,
        files=[*generation.files, *extra],
        stack=new_stack,
        model=generation.model,
        provider=generation.provider,
        demo_seed=generation.demo_seed,
    )


async def coremind_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    analysis = state.get("analysis")
    if not plan or not analysis:
        return {"error": "État pipeline incomplet (architect_plan manquant)."}

    if not state.get("builder_fallback", True) and state.get("generation"):
        await _step(
            cb,
            "coremind",
            "done",
            "Génération déjà fournie par BuilderAI — étape ignorée.",
            skipped=True,
        )
        return {}

    settings = _settings_from_config(config)
    prompt = _generation_user_prompt(state)
    type_label = plan.project_type_label
    generation_mode = state.get("generation_mode") or "client_demo"

    # --- Mode vitrine Next.js : scaffold fixe + contenu JSON (Phase 4.2b) ---
    if generation_mode == "vitrine_next":
        await _step(
            cb,
            "coremind",
            "start",
            f"Génération site vitrine Next.js ({type_label})…",
        )
        enriched_vitrine = (
            f"Type de projet : {type_label}.\n"
            f"Contexte : site vitrine multi-pages (accueil, services, contact).\n"
            f"Texte UI en français.\n\n"
            f"{PERSONALIZED_CONTENT_DIRECTIVE}\n\n"
            f"{build_toolbox_builder_context(plan)}"
            f"{prompt}"
        )
        try:
            vitrine = await build_vitrine_site(
                enriched_vitrine,
                project_type_label=type_label,
                settings=settings,
                project_id=state.get("project_id"),
                architect_plan=plan,
            )
        except (VitrineContentError, ScaffoldRenderError) as exc:
            return {"error": f"Génération vitrine : {exc}"}
        await _step(
            cb,
            "coremind",
            "done",
            (
                f"Scaffold vitrine — {vitrine.content.meta.businessName} · "
                f"{vitrine.file_count} fichier(s)"
                + (
                    f" · {vitrine.images_resolved} image(s) Unsplash"
                    if vitrine.images_resolved
                    else ""
                )
            ),
            template="vitrine_next",
            html_bytes=len(vitrine.generation.code or ""),
        )
        return {
            "generation": vitrine.generation,
            "preview_html": None,
        }

    # --- Mode "Vraie app" : génère un projet React/TypeScript complet ---
    if generation_mode == "real_app":
        await _step(
            cb,
            "coremind",
            "start",
            f"Génération application React/TypeScript ({type_label})…",
        )
        codegen = CodeGenService(settings)
        tier = CodeGenComplexity(analysis.complexity.value)
        enriched_real = (
            f"Type de projet : {type_label}.\n"
            f"Contexte : application React/TypeScript déployable sur Railway ou Vercel.\n"
            f"Texte UI en français.\n\n"
            f"{PERSONALIZED_CONTENT_DIRECTIVE}\n\n"
            f"{build_toolbox_builder_context(plan)}"
            f"{prompt}"
        )
        generation = await codegen.generate_code(
            enriched_real,
            tier,
            demo_html=False,
            project_id=state.get("project_id"),
        )
        generation = apply_toolbox_to_generation(
            generation, plan, project_id=state.get("project_id")
        )
        generation = _inject_package_json(generation, type_label, plan=plan)
        code_chars = len(generation.code or "")
        file_count = len(generation.files)
        await _step(
            cb,
            "coremind",
            "done",
            f"App React générée — {file_count} fichier(s), {code_chars} chars · {generation.model}",
            template="real_app",
            html_bytes=code_chars,
        )
        return {
            "generation": generation,
            # Pas d'aperçu HTML : le code React n'est pas rendu directement.
            "preview_html": None,
        }

    # --- Template-first (ecommerce, réservation, app, desktop) : pas de dashboard premium ---
    from agents.template_first_policy import is_template_first_html_project

    if is_template_first_html_project(plan, generation_mode=generation_mode):
        sector_tpl = state.get("sector_template")
        await _step(
            cb,
            "coremind",
            "start",
            "Reprise assemblage template sectoriel (évite template premium dashboard)…",
        )
        builder = BuilderAgent(settings)
        retry = await builder.build(
            prompt,
            plan=plan,
            analysis=analysis,
            settings=settings,
            project_id=state.get("project_id"),
            design_system=state.get("design_system"),
            sector_template_html=_sector_template_html_from_state(state),
            sector_template=sector_tpl,
            research_brief=state.get("research_brief"),
            generation_mode=generation_mode,
        )
        if not retry.fallback_to_coremind and retry.generation:
            tid = (
                str(sector_tpl.get("template_id"))
                if isinstance(sector_tpl, dict)
                else "?"
            )
            logger.info(
                "[CoreMindAI] reprise template-first OK | sector_template_id=%s | model=%s",
                tid,
                getattr(retry.generation, "model", "?"),
            )
            await _step(
                cb,
                "coremind",
                "done",
                f"Assemblage sectoriel — {getattr(retry.generation, 'model', 'template')}",
                template=tid,
            )
            retry_preview = retry.preview_html
            return {
                "generation": retry.generation,
                "assembled_html": retry_preview,
                "preview_html": retry_preview,
                "builder_fallback": False,
            }
        logger.warning(
            "[CoreMindAI] reprise template-first échouée — fallback demo premium (%s)",
            plan.template,
        )

    # --- Mode "Démo client" (par défaut) : pipeline HTML premium TaskFlow ---
    await _step(cb, "coremind", "start", "Génération HTML et seed adaptée au template…")
    enriched = (
        f"Type de projet cible : {type_label}.\n"
        f"Template premium : {plan.template_label} ({plan.template}).\n\n"
        f"{PERSONALIZED_CONTENT_DIRECTIVE}\n\n"
        f"{build_toolbox_builder_context(plan)}"
        f"{prompt}"
    )

    svc = DemoTemplateService(settings)
    seed: DemoSeedData = await svc.resolve_seed(
        enriched,
        project_type_label=type_label,
        template_hint=plan.template,
        project_id=state.get("project_id"),
    )
    seed = replace(
        seed,
        template=plan.template,
        subtitle=seed.subtitle
        if seed.template == plan.template
        else seed.subtitle,
    )
    seed = align_seed_template(seed, enriched, project_type_label=type_label)
    if seed.template != plan.template:
        seed = replace(seed, template=plan.template)

    document = await build_client_demo_document(
        enriched,
        project_type_label=type_label,
        settings=settings,
        seed=seed,
        project_id=state.get("project_id"),
    )
    preview_html = preview_html_from_generation(
        document.generation,
        title=type_label,
        user_prompt=enriched,
    )
    await _step(
        cb,
        "coremind",
        "done",
        f"HTML généré ({document.html_bytes} octets, template {document.template})",
        template=document.template,
        html_bytes=document.html_bytes,
    )
    return {
        "generation": document.generation,
        "preview_html": preview_html,
    }


async def visionui_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    preview_html = state.get("preview_html")
    generation = state.get("generation")
    if not plan:
        return {"error": "État pipeline incomplet (VisionUI)."}

    generation_mode = state.get("generation_mode") or "client_demo"
    if generation_mode in ("real_app", "vitrine_next"):
        await _step(
            cb,
            "visionui",
            "done",
            "Aperçu HTML non applicable — étape ignorée.",
        )
        return {}

    html = (preview_html or "").strip()
    if not html and generation is not None:
        html = (getattr(generation, "code", None) or "").strip()

    if not html:
        await _step(cb, "visionui", "done", "Aucun HTML à capturer — étape ignorée.")
        return {}

    await _step(
        cb,
        "visionui",
        "start",
        "Médias toolbox (photos, icônes, illustrations) puis capture…",
    )
    settings = _settings_from_config(config)
    agent = VisionUIAgent(settings)
    result = await agent.capture(
        html,
        title=plan.project_type_label,
        settings=settings,
        project_id=state.get("project_id"),
        project_type=plan.project_type_label,
        architect_plan=plan,
        prompt=state.get("prompt"),
    )
    source_label = "Replicate" if result.preview_source == "replicate" else "HTML local"

    await _step(
        cb,
        "visionui",
        "done",
        result.preview.message or f"Aperçu VisionUI ({source_label}).",
        vision_screenshot_url=result.screenshot_url,
        vision_preview_source=result.preview_source,
        vision_local_html=result.preview.local_html if result.preview_source == "local" else None,
    )
    return {
        "vision_screenshot_url": result.screenshot_url,
        "vision_preview_source": result.preview_source,
        "preview_html": result.preview.local_html or preview_html,
    }


async def bughunter_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from agents.bug_hunter_agent import (
        client_literal_issues_only,
        repair_generation_client_literals,
    )
    from agents.vitrine_policy import is_vitrine_html_project
    from tools.client_content_profile import (
        CLIENT_LITERAL_ISSUE_CODES,
        build_client_content_profile,
        log_client_content_context,
    )

    cb = _callback_from_config(config)
    generation = state.get("generation")
    plan = state.get("architect_plan")
    if not generation or not plan:
        return {"error": "État pipeline incomplet (génération manquante)."}

    await _step(cb, "bughunter", "start", "Vérification du HTML généré…")
    settings = _settings_from_config(config)
    hunter = BugHunterAgent(settings)
    user_prompt = state.get("prompt") or ""
    research_brief = state.get("research_brief")
    client_profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_brief,
        plan=plan,
    )
    log_client_content_context(client_profile, prefix="BugHunterAI")

    report = hunter.analyze_generation(
        generation,
        title=plan.project_type_label,
        research_brief=research_brief,
        architect_plan=plan,
        user_prompt=user_prompt,
    )

    patched_generation = generation
    literal_repaired = False
    if (
        client_profile.company_name
        and is_vitrine_html_project(plan, generation_mode=state.get("generation_mode"))
        and not report.ok
        and CLIENT_LITERAL_ISSUE_CODES.intersection(report.issue_codes)
    ):
        patched_generation, report = repair_generation_client_literals(
            generation,
            client_profile,
            title=plan.project_type_label,
            research_brief=research_brief,
            architect_plan=plan,
            user_prompt=user_prompt,
            settings=settings,
        )
        literal_repaired = True

    preview_html = preview_html_from_generation(
        patched_generation,
        title=plan.project_type_label,
        user_prompt=user_prompt,
    )

    msg = (
        "Aucun problème détecté."
        if report.ok
        else f"{len(report.issues)} problème(s) : {', '.join(report.issue_codes[:6])}"
    )
    if literal_repaired and report.ok:
        msg = "Identité client injectée — HTML validé."
    elif literal_repaired:
        msg = (
            "Identité client injectée — "
            + (
                "alertes restantes non liées au client."
                if not client_literal_issues_only(report.issue_codes)
                else "vérification partielle."
            )
        )

    from agents.bug_hunter_agent import has_vitrine_blocking_issues
    from agents.vitrine_policy import is_vitrine_html_project

    vitrine_project = is_vitrine_html_project(
        plan, generation_mode=state.get("generation_mode")
    )
    blocking = has_vitrine_blocking_issues(report) if vitrine_project else not report.ok
    await _step(
        cb,
        "bughunter",
        "done",
        msg,
        ok=report.ok or not blocking,
        issue_count=len(report.issues),
    )
    out: dict[str, Any] = {"bug_report": report}
    if literal_repaired:
        out["generation"] = patched_generation
        out["preview_html"] = preview_html
    return out


def _route_after_bughunter(state: PipelineState) -> str:
    from agents.bug_hunter_agent import has_vitrine_blocking_issues
    from agents.vitrine_policy import is_vitrine_html_project

    report = state.get("bug_report")
    if report and report.ok:
        return "testpilot"
    plan = state.get("architect_plan")
    vitrine = bool(
        plan
        and is_vitrine_html_project(plan, generation_mode=state.get("generation_mode"))
    )
    if vitrine and report and not has_vitrine_blocking_issues(report):
        return "testpilot"
    loops = state.get("fix_loops") or 0
    if loops >= MAX_AUTOFIX_LOOPS:
        return "testpilot"
    if report and not vitrine:
        return "autofix"
    if vitrine and report and has_vitrine_blocking_issues(report):
        return "autofix"
    return "testpilot"


async def autofix_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from agents.bug_hunter_agent import (
        client_literal_issues_only,
        repair_generation_client_literals,
    )
    from agents.vitrine_policy import is_vitrine_html_project
    from tools.client_content_profile import (
        CLIENT_LITERAL_ISSUE_CODES,
        build_client_content_profile,
    )

    cb = _callback_from_config(config)
    report = state.get("bug_report")
    analysis = state.get("analysis")
    plan = state.get("architect_plan")
    generation = state.get("generation")
    if not report or not analysis or not plan or not generation:
        return {"error": "État pipeline incomplet (autofix)."}

    loop_num = (state.get("fix_loops") or 0) + 1
    user_prompt = state.get("prompt") or ""

    if loop_num > MAX_AUTOFIX_LOOPS:
        profile = build_client_content_profile(
            user_prompt=user_prompt,
            research_brief=state.get("research_brief"),
            plan=plan,
        )
        if profile.company_name and is_vitrine_html_project(
            plan, generation_mode=state.get("generation_mode")
        ):
            generation, report = repair_generation_client_literals(
                generation,
                profile,
                title=plan.project_type_label,
                research_brief=state.get("research_brief"),
                architect_plan=plan,
                user_prompt=user_prompt,
                settings=_settings_from_config(config),
            )
        preview_html = preview_html_from_generation(
            generation,
            title=plan.project_type_label,
            user_prompt=user_prompt,
        )
        await _step(
            cb,
            "autofix",
            "done",
            f"Limite {MAX_AUTOFIX_LOOPS} boucles AutoFix — livraison avec avertissements.",
            ok=True,
            loop=loop_num,
        )
        return {
            "generation": generation,
            "preview_html": preview_html,
            "bug_report": report,
            "fix_loops": loop_num,
        }

    if CLIENT_LITERAL_ISSUE_CODES.intersection(report.issue_codes):
        profile = build_client_content_profile(
            user_prompt=user_prompt,
            research_brief=state.get("research_brief"),
            plan=plan,
        )
        if profile.company_name and is_vitrine_html_project(
            plan, generation_mode=state.get("generation_mode")
        ):
            settings = _settings_from_config(config)
            generation, report = repair_generation_client_literals(
                generation,
                profile,
                title=plan.project_type_label,
                research_brief=state.get("research_brief"),
                architect_plan=plan,
                user_prompt=user_prompt,
                settings=settings,
            )
            preview_html = preview_html_from_generation(
                generation,
                title=plan.project_type_label,
                user_prompt=user_prompt,
            )
            await _step(
                cb,
                "autofix",
                "done",
                "Identité client injectée (sans régénération LLM)."
                if report.ok
                else "Post-traitement client appliqué.",
                ok=report.ok or client_literal_issues_only(report.issue_codes),
                loop=loop_num,
            )
            return {
                "generation": generation,
                "preview_html": preview_html,
                "bug_report": report,
                "fix_loops": loop_num,
            }
    await _step(
        cb,
        "autofix",
        "start",
        f"Correction automatique (boucle {loop_num}/{MAX_AUTOFIX_LOOPS})…",
        loop=loop_num,
    )
    settings = _settings_from_config(config)
    tier = CodeGenComplexity(analysis.complexity.value)
    prompt = state["prompt"].strip()
    enriched = (
        f"Type de projet : {plan.project_type_label}.\n"
        f"Template : {plan.template_label}.\n\n{prompt}"
    )

    fixer = AutoFixAgent(settings)
    generation, attempts, new_report = await fixer.repair(
        user_prompt=enriched,
        tier=tier,
        title=plan.project_type_label,
        initial_report=report,
        project_id=state.get("project_id"),
        plan=plan,
        analysis=analysis,
        generation_mode=state.get("generation_mode"),
    )
    preview_html = preview_html_from_generation(
        generation,
        title=plan.project_type_label,
        user_prompt=enriched,
    )
    await _step(
        cb,
        "autofix",
        "done",
        "HTML corrigé et revalidé."
        if new_report.ok
        else f"Correction partielle ({len(new_report.issues)} alerte(s) restantes).",
        ok=new_report.ok,
        attempts=attempts,
        loop=loop_num,
    )
    return {
        "generation": generation,
        "preview_html": preview_html,
        "bug_report": new_report,
        "fix_loops": loop_num,
        "autofix_attempts": attempts,
    }


async def testpilot_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    generation = state.get("generation")
    plan = state.get("architect_plan")
    preview_html = state.get("preview_html")
    if not generation or not plan:
        return {"error": "État pipeline incomplet (TestPilotAI)."}

    await _step(cb, "testpilot", "start", "Validation rendu, liens et scripts JS…")
    settings = _settings_from_config(config)
    agent = TestPilotAgent(settings)
    prompt = state["prompt"].strip()
    enriched = (
        f"Type : {plan.project_type_label}.\n"
        f"Template : {plan.template_label}.\n\n{prompt}"
    )
    report = agent.validate_generation(
        generation,
        title=plan.project_type_label,
        user_prompt=enriched,
    )

    fix_loops = state.get("fix_loops") or 0
    refix_loops = state.get("testpilot_refix_loops") or 0

    if report.ok:
        if refix_loops > 0 or fix_loops > 0:
            validation_status = "corrected"
            badge_label = "Corrigé"
        else:
            validation_status = "validated"
            badge_label = "Validé"
        await _step(
            cb,
            "testpilot",
            "done",
            f"Validation réussie — {badge_label}.",
            ok=True,
            validation_status=validation_status,
            validation_badge=badge_label,
            checks_run=report.checks_run,
        )
        return {
            "testpilot_report": report,
            "validation_status": validation_status,
        }

    next_refix = refix_loops + 1
    await _step(
        cb,
        "testpilot",
        "done",
        f"{len(report.issues)} échec(s) de validation — "
        + (
            "renvoi vers AutoFixAI."
            if next_refix <= MAX_TESTPILOT_AUTOFIX_LOOPS
            else "finalisation avec avertissements."
        ),
        ok=False,
        validation_status="corrected",
        validation_badge="Corrigé",
        issue_count=len(report.issues),
    )
    return {
        "testpilot_report": report,
        "testpilot_refix_loops": next_refix,
        "bug_report": testpilot_to_bug_report(report),
        "validation_status": "corrected",
    }


def _route_after_testpilot(state: PipelineState) -> str:
    report = state.get("testpilot_report")
    if report and getattr(report, "ok", False):
        if _playwright_requested(state):
            return "playwright"
        if _lighthouse_requested(state):
            return "lighthouse"
        return "export"
    refix = state.get("testpilot_refix_loops") or 0
    fix_loops = state.get("fix_loops") or 0
    if refix > MAX_TESTPILOT_AUTOFIX_LOOPS or fix_loops >= MAX_AUTOFIX_LOOPS:
        if _playwright_requested(state):
            return "playwright"
        if _lighthouse_requested(state):
            return "lighthouse"
        return "export"
    return "autofix"


def _playwright_requested(state: PipelineState) -> bool:
    if state.get("playwright_enabled") is False:
        return False
    return get_settings().playwright_enabled


def _lighthouse_requested(state: PipelineState) -> bool:
    if state.get("lighthouse_enabled") is False:
        return False
    return get_settings().lighthouse_enabled


async def playwright_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    preview_html = state.get("preview_html") or ""
    generation = state.get("generation")
    if generation and not preview_html:
        from agents.demo_quality import preview_html_from_generation

        plan = state.get("architect_plan")
        preview_html = preview_html_from_generation(
            generation,
            title=plan.project_type_label if plan else "Projet",
            user_prompt=state.get("prompt", ""),
        )

    await _step(cb, "playwright", "start", "Tests E2E Chromium (Playwright)…")
    settings = _settings_from_config(config)
    agent = PlaywrightAgent(settings)
    from agents.vitrine_policy import is_vitrine_html_project
    from tools.vitrine_html_enhance import enhance_builder_vitrine_html

    plan = state.get("architect_plan")
    user_prompt = state.get("prompt") or ""
    vitrine = bool(
        plan
        and is_vitrine_html_project(plan, generation_mode=state.get("generation_mode"))
    )

    test_html = str(preview_html)
    if vitrine and test_html.strip():
        test_html = enhance_builder_vitrine_html(
            test_html,
            plan=plan,
            research_brief=state.get("research_brief"),
            user_prompt=user_prompt,
        )
        if generation:
            from agents.demo_quality import code_result_from_html

            generation = code_result_from_html(
                test_html,
                summary=getattr(generation, "summary", "") or "Vitrine HTML",
                model=getattr(generation, "model", "pipeline"),
                provider=getattr(generation, "provider", "cyberforge"),
            )
            preview_html = test_html

    # Ne jamais tester une URL Railway/Vercel avant export — HTML local uniquement.
    report = await agent.test_site(
        html=test_html,
        base_url=None,
        settings=settings,
        vitrine_mode=vitrine,
        prefer_local_preview=True,
    )

    refix_loops = state.get("playwright_autofix_loops") or 0
    threshold = settings.playwright_pass_threshold

    if report.ok or report.skipped:
        await _step(
            cb,
            "playwright",
            "done",
            f"Tests Playwright OK — score {report.score}/100.",
            ok=True,
            playwright_score=report.score,
            playwright_passed=report.passed,
            playwright_failed=report.failed,
        )
        out: dict[str, Any] = {"playwright_report": report}
        if vitrine and test_html:
            out["generation"] = generation
            out["preview_html"] = preview_html
        return out

    await _step(
        cb,
        "playwright",
        "done",
        f"Avertissement Playwright — score {report.score}/{threshold} (non bloquant).",
        ok=True,
        playwright_score=report.score,
        playwright_passed=report.passed,
        playwright_failed=report.failed,
    )
    fail_out: dict[str, Any] = {
        "playwright_report": report,
    }
    if vitrine and test_html:
        fail_out["generation"] = generation
        fail_out["preview_html"] = preview_html
    return fail_out


def _route_after_playwright(state: PipelineState) -> str:
    """Playwright — avertissement non bloquant (pas de boucle AutoFix)."""
    if state.get("error"):
        return "finalize"
    return "lighthouse" if _lighthouse_requested(state) else "export"


async def lighthouse_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    preview_html = state.get("preview_html") or ""
    generation = state.get("generation")
    if generation and not preview_html:
        plan = state.get("architect_plan")
        preview_html = preview_html_from_generation(
            generation,
            title=plan.project_type_label if plan else "Projet",
            user_prompt=state.get("prompt", ""),
        )

    await _step(cb, "lighthouse", "start", "Audit Lighthouse (Performance, SEO, A11y)…")
    settings = _settings_from_config(config)
    agent = LighthouseAgent(settings)
    production_url = None
    export_data = state.get("export_result")
    if export_data is not None:
        production_url = getattr(export_data, "production_url", None)

    report = await agent.audit_site(
        html=str(preview_html),
        base_url=production_url,
        settings=settings,
    )

    refix_loops = state.get("lighthouse_autofix_loops") or 0
    threshold = settings.lighthouse_pass_threshold

    if report.ok or report.skipped:
        await _step(
            cb,
            "lighthouse",
            "done",
            f"Lighthouse OK — score global {report.score_global}/100.",
            ok=True,
            lighthouse_score_global=report.score_global,
            lighthouse_performance=report.performance,
            lighthouse_seo=report.seo,
            lighthouse_accessibility=report.accessibility,
            lighthouse_best_practices=report.best_practices,
        )
        return {"lighthouse_report": report}

    await _step(
        cb,
        "lighthouse",
        "done",
        f"Avertissement Lighthouse — score {report.score_global}/{threshold} (non bloquant).",
        ok=True,
        lighthouse_score_global=report.score_global,
        lighthouse_performance=report.performance,
        lighthouse_seo=report.seo,
        lighthouse_accessibility=report.accessibility,
        lighthouse_best_practices=report.best_practices,
        lighthouse_recommendations=report.recommendations,
    )
    return {
        "lighthouse_report": report,
    }


def _route_after_lighthouse(state: PipelineState) -> str:
    """Lighthouse — avertissement non bloquant (pas de boucle AutoFix)."""
    if state.get("error"):
        return "finalize"
    return "export"


async def export_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    if state.get("error"):
        await _step(cb, "export", "done", "Export ignoré (erreur pipeline).")
        return {}

    plan = state.get("architect_plan")
    analysis = state.get("analysis")
    generation = state.get("generation")
    if not plan or not analysis or not generation:
        await _step(cb, "export", "done", "Export ignoré (génération incomplète).")
        return {}

    generation_mode = state.get("generation_mode") or "client_demo"
    if plan.project_type == ProjectType.EXTENSION_NAVIGATEUR:
        await _step(cb, "export", "start", "Export ZIP extension Chrome…")
    personal = bool(state.get("personal_project"))
    if personal and generation_mode == "real_app":
        await _step(
            cb,
            "export",
            "start",
            "Déploiement Cloudflare Pages dédié (URL *.pages.dev)…",
        )
    elif generation_mode in ("real_app", "vitrine_next"):
        label = (
            "Déploiement site vitrine Next.js (Vercel)…"
            if generation_mode == "vitrine_next"
            else "Déploiement application React (Railway / Vercel)…"
        )
        await _step(cb, "export", "start", label)
    else:
        await _step(cb, "export", "start", "Déploiement automatique (Cloudflare / Railway / GitHub)…")

    settings = _settings_from_config(config)
    agent = ExportAgent(settings)
    sector_tpl = state.get("sector_template")
    template_id = (
        str(sector_tpl.get("template_id"))
        if isinstance(sector_tpl, dict) and sector_tpl.get("template_id")
        else None
    )
    from agents.template_first_policy import is_template_first_html_project

    expect_sector = is_template_first_html_project(
        plan, generation_mode=generation_mode
    )
    # Pas d'aperçu HTML pour React / vitrine Next (évite export Cloudflare démo).
    if generation_mode in ("real_app", "vitrine_next"):
        assembled_html = ""
        preview_html = ""
    else:
        assembled_html = str(state.get("assembled_html") or "")
        preview_html = str(state.get("preview_html") or "")

    result = await agent.export(
        state["prompt"],
        plan=plan,
        analysis=analysis,
        generation=generation,
        assembled_html=assembled_html,
        preview_html=str(preview_html),
        template_id=template_id,
        sector_template=sector_tpl if isinstance(sector_tpl, dict) else None,
        expect_sector_template=expect_sector,
        settings=settings,
        project_id=state.get("project_id"),
        generation_mode=generation_mode,
        personal_project=personal,
        pages_project_slug=state.get("pages_project_slug"),
        project_title=state.get("project_title"),
        extension_files=state.get("extension_files"),
    )

    await _step(
        cb,
        "export",
        "done",
        result.message or "Export terminé.",
        ok=result.success,
        production_url=result.production_url,
        export_provider=result.provider,
        artifact_download_url=result.artifact_download_url,
        github_url=result.github_url,
        unlock_url=result.unlock_url,
        newsletter_triggered=bool(getattr(result, "newsletter_triggered", False)),
    )
    out: dict[str, Any] = {"export_result": result}
    if result.artifact_download_url:
        out["artifact_download_url"] = result.artifact_download_url
    return out


async def finalize_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    if state.get("error"):
        await _step(cb, "finalize", "error", state["error"])
        return {}

    analysis = state.get("analysis")
    generation = state.get("generation")
    architect = state.get("architect_plan")
    preview_html = state.get("preview_html")
    if not analysis or not generation or not architect:
        return {"error": "Pipeline terminé sans résultat exploitable."}

    from agents.demo_quality import code_result_from_html
    from tools.export_html_resolve import (
        force_finalize_preview_from_assembled,
        resolve_pipeline_preview_html,
    )
    from tools.html_markdown import strip_markdown_code_fences

    if generation:
        from tools.codegen_service import CodeGenerateResult, GeneratedFile

        files_out: list[GeneratedFile] = []
        for f in getattr(generation, "files", None) or []:
            path = str(getattr(f, "path", "") or "")
            content = str(getattr(f, "content", "") or "")
            if path.lower().endswith((".html", ".htm")):
                content = strip_markdown_code_fences(content)
            files_out.append(GeneratedFile(path=path, content=content))
        generation = CodeGenerateResult(
            summary=generation.summary,
            code=strip_markdown_code_fences(str(getattr(generation, "code", None) or "")),
            files=files_out or list(getattr(generation, "files", None) or []),
            stack=list(generation.stack),
            model=generation.model,
            provider=generation.provider,
            demo_seed=generation.demo_seed,
        )

    sector_tpl = state.get("sector_template")
    sector_html = None
    if isinstance(sector_tpl, dict):
        sector_html = sector_tpl.get("html") or sector_tpl.get("html_raw")

    from tools.extension_pipeline import (
        extract_extension_popup_html,
        is_extension_project_type,
        prepare_extension_preview_html,
    )

    is_extension = (
        architect.project_type == ProjectType.EXTENSION_NAVIGATEUR
        or is_extension_project_type(architect)
    )

    ext_files = state.get("extension_files")
    ext_files_dict = ext_files if isinstance(ext_files, dict) else None

    state_assembled_raw = strip_markdown_code_fences(
        str(state.get("assembled_html") or "")
    )
    asm_present = bool(state_assembled_raw.strip())
    asm_bytes = len(state_assembled_raw.encode("utf-8")) if asm_present else 0

    if is_extension:
        popup_raw, popup_js = extract_extension_popup_html(
            extension_files=ext_files_dict,
            generation=generation,
            assembled_html=state.get("assembled_html"),
            preview_html=preview_html,
        )
        if popup_raw.strip():
            preview_html = prepare_extension_preview_html(
                popup_raw,
                popup_js=popup_js,
                prompt=state.get("prompt") or "",
            )
            assembled_html = popup_raw
            asm_present = True
            asm_bytes = len(popup_raw.encode("utf-8"))
            logger.info(
                "[finalize] extension popup.html -> preview_html (%d bytes, js_inlined=%s)",
                len((preview_html or "").encode("utf-8")),
                bool(popup_js.strip()),
            )
        else:
            logger.warning("[finalize] extension_navigateur sans popup.html exploitable")
            preview_html = preview_html or ""
            assembled_html = assembled_html or preview_html
    elif asm_present:
        from tools.demo_preview_gate import prepare_internal_app_preview_html

        preview_html = (
            prepare_internal_app_preview_html(state_assembled_raw)
            or state_assembled_raw
        )
        assembled_html = preview_html
    else:
        preview_html, assembled_html = resolve_pipeline_preview_html(
            assembled_html=state.get("assembled_html"),
            preview_html=preview_html,
            sector_template_html=sector_html,
            generation=generation,
            title=architect.project_type_label,
            user_prompt=state.get("prompt") or "",
        )
        preview_html, assembled_html = force_finalize_preview_from_assembled(
            state_assembled_html=state.get("assembled_html"),
            preview_html=preview_html,
            assembled_html=assembled_html,
            sector_template_html=sector_html,
            generation=generation,
            title=architect.project_type_label,
            user_prompt=state.get("prompt") or "",
        )

    preview_saved = bool((preview_html or "").strip())
    logger.info(
        "[finalize] assembled_html present=%s bytes=%d | preview_html saved=%s",
        asm_present,
        asm_bytes,
        preview_saved,
    )
    if preview_html and generation:
        if is_extension:
            gen_files = list(getattr(generation, "files", None) or [])
            if ext_files_dict and not gen_files:
                from tools.codegen_service import GeneratedFile

                gen_files = [
                    GeneratedFile(path=path, content=content)
                    for path, content in sorted(ext_files_dict.items())
                ]
            generation = CodeGenerateResult(
                summary=generation.summary or "Extension Chrome MV3",
                code=preview_html,
                files=gen_files,
                stack=list(generation.stack),
                model=generation.model,
                provider=generation.provider,
                demo_seed=generation.demo_seed,
            )
        else:
            generation = code_result_from_html(
                preview_html,
                summary=generation.summary or "HTML livrable",
                model=generation.model,
                provider=generation.provider,
            )

    await _step(cb, "finalize", "start", "Assemblage de la réponse…")
    settings = _settings_from_config(config)
    cfg = _configurable(config)
    started = cfg.get("pipeline_started")
    if isinstance(started, (int, float)):
        duration_ms = max(1, int((time.perf_counter() - started) * 1000))
    else:
        duration_ms = 1
    codegen = CodeGenService(settings)
    tier = CodeGenComplexity(analysis.complexity.value)

    generation_mode = state.get("generation_mode") or "client_demo"
    if generation_mode == "vitrine_next":
        template = "vitrine_next"
    elif generation_mode == "real_app":
        template = "real_app"
    else:
        template = architect.template
    html_bytes = len((preview_html or generation.code or "").encode("utf-8"))
    pipeline_info = DemoPipelineSummary(
        template=template,
        seed_personalized=bool(
            generation.demo_seed and generation.demo_seed.get("llm_personalized")
        ),
        html_bytes=html_bytes,
    )

    seed_input_chars = len(state["prompt"])
    output_chars = len(generation.code or "")
    cost = (
        estimate_cost_usd(
            generation.provider,
            generation.model,
            seed_input_chars,
            output_chars,
        )
        if generation.provider != TEMPLATE_PROVIDER
        else 0.0
    )

    planned = (
        codegen.planned_models(tier)
        if codegen.is_configured()
        else [f"{TEMPLATE_PROVIDER} · {TEMPLATE_MODEL} (template préfabriqué)"]
    )

    metrics = GenerationMetrics(
        model=generation.model,
        provider=generation.provider,
        complexity=analysis.complexity,
        complexity_score=analysis.complexity_score,
        duration_ms=duration_ms,
        estimated_cost_usd=cost,
        project_type_selected=architect.project_type_label
        if state.get("project_type_hint")
        else None,
    )

    tp_report = state.get("testpilot_report")
    validation_status = state.get("validation_status")
    if not validation_status:
        validation_status = "validated" if (tp_report and tp_report.ok) else "corrected"
    testpilot_passed = bool(tp_report and tp_report.ok)
    summary = None
    if tp_report:
        summary = (
            "Validation TestPilotAI réussie."
            if tp_report.ok
            else f"Validation partielle ({len(tp_report.issues)} alerte(s))."
        )

    export_data = state.get("export_result")
    export_manifest = None
    production_url = None
    export_provider = None
    github_export_url = None
    demo_token = None
    demo_password = None
    unlock_url = None
    artifact_download_url = state.get("artifact_download_url")
    if export_data is not None:
        export_manifest = getattr(export_data, "manifest", None)
        production_url = getattr(export_data, "production_url", None)
        export_provider = getattr(export_data, "provider", None)
        artifact_download_url = artifact_download_url or getattr(
            export_data, "artifact_download_url", None
        )
        github_export_url = getattr(export_data, "github_url", None)
        demo_token = getattr(export_data, "demo_token", None)
        demo_password = getattr(export_data, "demo_password", None)
        unlock_url = getattr(export_data, "unlock_url", None)

    pw_report = state.get("playwright_report")
    pw_score = getattr(pw_report, "score", None) if pw_report else None
    pw_dump = pw_report.model_dump() if pw_report is not None else None

    lh_report = state.get("lighthouse_report")
    lh_score = getattr(lh_report, "score_global", None) if lh_report else None
    lh_dump = lh_report.model_dump() if lh_report is not None else None

    result = CoreMindRunResult(
        analysis=analysis,
        architect_plan=architect,
        design_system=state.get("design_system"),
        generation=generation,
        metrics=metrics,
        planned_models=planned,
        demo_pipeline=pipeline_info,
        preview_html=preview_html,
        assembled_html=assembled_html or preview_html,
        vision_screenshot_url=state.get("vision_screenshot_url"),
        vision_preview_source=state.get("vision_preview_source"),
        testpilot_passed=testpilot_passed,
        validation_status=validation_status,
        testpilot_summary=summary,
        playwright_score=pw_score,
        playwright_report=pw_dump,
        lighthouse_score_global=lh_score,
        lighthouse_report=lh_dump,
        export_manifest=export_manifest,
        production_url=production_url,
        export_provider=export_provider,
        artifact_download_url=artifact_download_url,
        github_export_url=github_export_url,
        demo_token=demo_token,
        demo_password=demo_password,
        unlock_url=unlock_url,
    )
    await _step(cb, "finalize", "done", "Génération terminée.")
    return {"result": result}


def build_pipeline_graph() -> Any:
    """
    Compile le graphe LangGraph.

    Vitrine (client_demo / vitrine_next) :
      Architect → [Research] → DesignSystem → Template → [Stitch] → Content
      → Builder → VisionUI → BugHunter → … → Export → Finalisation

    real_app : même préambule visuel optionnel, puis Builder (LLM) ou CoreMind si échec.
    """
    graph = StateGraph(PipelineState)
    graph.add_node("architect", architect_node)
    graph.add_node(NODE_DATABASE, database_ai_node)
    graph.add_node(NODE_AUTH, auth_ai_node)
    graph.add_node(NODE_ELECTRON, electron_ai_node)
    graph.add_node(NODE_DESIGN_SYSTEM, design_system_node)
    graph.add_node("extension_build", extension_build_node)
    graph.add_node("template_ai", template_ai_node)
    graph.add_node("content_ai", content_ai_node)
    graph.add_node("research", research_node)
    graph.add_node("stitch", stitch_node)
    graph.add_node("openhands", openhands_node)
    graph.add_node("builder", builder_node)
    graph.add_node("coremind", coremind_node)
    graph.add_node("visionui", visionui_node)
    graph.add_node("bughunter", bughunter_node)
    graph.add_node("autofix", autofix_node)
    graph.add_node("testpilot", testpilot_node)
    graph.add_node("playwright", playwright_node)
    graph.add_node("lighthouse", lighthouse_node)
    graph.add_node("export", export_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("architect")
    graph.add_conditional_edges(
        "architect",
        _route_after_architect,
        {
            NODE_DATABASE: NODE_DATABASE,
            "research": "research",
            NODE_DESIGN_SYSTEM: NODE_DESIGN_SYSTEM,
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        NODE_DATABASE,
        _route_after_database_ai,
        {
            NODE_AUTH: NODE_AUTH,
            "research": "research",
            NODE_DESIGN_SYSTEM: NODE_DESIGN_SYSTEM,
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        NODE_AUTH,
        _route_after_auth_ai,
        {
            "research": "research",
            NODE_DESIGN_SYSTEM: NODE_DESIGN_SYSTEM,
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        NODE_ELECTRON,
        _route_after_electron_ai,
        {
            "research": "research",
            NODE_DESIGN_SYSTEM: NODE_DESIGN_SYSTEM,
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "research",
        _route_after_research,
        {
            NODE_DESIGN_SYSTEM: NODE_DESIGN_SYSTEM,
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        NODE_DESIGN_SYSTEM,
        _route_after_design_system,
        {
            "extension_build": "extension_build",
            "template_ai": "template_ai",
            "finalize": "finalize",
        },
    )
    graph.add_edge("extension_build", "export")
    graph.add_conditional_edges(
        "template_ai",
        _route_after_template_ai,
        {
            "stitch": "stitch",
            "content_ai": "content_ai",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "content_ai",
        _route_after_content_ai,
        {
            "stitch": "stitch",
            "openhands": "openhands",
            "coremind": "coremind",
            "builder": "builder",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "stitch",
        _route_after_stitch,
        {
            "content_ai": "content_ai",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "openhands",
        _route_after_openhands,
        {"coremind": "coremind", "visionui": "visionui", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "builder",
        _route_after_builder,
        {"coremind": "coremind", "visionui": "visionui", "finalize": "finalize"},
    )
    graph.add_edge("coremind", "visionui")
    graph.add_edge("visionui", "bughunter")
    graph.add_conditional_edges(
        "bughunter",
        _route_after_bughunter,
        {"testpilot": "testpilot", "autofix": "autofix"},
    )
    graph.add_edge("autofix", "visionui")
    graph.add_conditional_edges(
        "testpilot",
        _route_after_testpilot,
        {
            "playwright": "playwright",
            "lighthouse": "lighthouse",
            "export": "export",
            "autofix": "autofix",
        },
    )
    graph.add_conditional_edges(
        "playwright",
        _route_after_playwright,
        {
            "lighthouse": "lighthouse",
            "export": "export",
            "autofix": "autofix",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "lighthouse",
        _route_after_lighthouse,
        {"export": "export", "autofix": "autofix", "finalize": "finalize"},
    )
    graph.add_edge("export", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


_compiled_graph: Any | None = None


def get_compiled_pipeline() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_pipeline_graph()
    return _compiled_graph


async def run_generation_pipeline(
    prompt: str,
    *,
    project_type_hint: ProjectType | None = None,
    generation_mode: str | None = None,
    openhands_enabled: bool | None = None,
    playwright_enabled: bool | None = None,
    lighthouse_enabled: bool | None = None,
    research_enabled: bool | None = None,
    stitch_enabled: bool | None = None,
    project_id: str | None = None,
    inspiration_brief: str | None = None,
    personal_project: bool = False,
    pages_project_slug: str | None = None,
    project_title: str | None = None,
    settings: Settings | None = None,
    on_event: PipelineEventCallback | None = None,
) -> CoreMindRunResult:
    """
    Exécute le pipeline complet et retourne le résultat CoreMindRunResult.
    Émet des événements step_* via on_event si fourni (SSE frontend).
    generation_mode : "client_demo" (défaut), "real_app" ou "vitrine_next".
    """
    resolved_settings = settings or get_settings()
    pipeline_started = time.perf_counter()
    brief = (inspiration_brief or "").strip() or None
    initial: PipelineState = {
        "prompt": prompt.strip(),
        "inspiration_brief": brief,
        "project_id": project_id,
        "project_type_hint": project_type_hint,
        "generation_mode": generation_mode or "client_demo",
        "openhands_enabled": openhands_enabled,
        "playwright_enabled": playwright_enabled,
        "lighthouse_enabled": lighthouse_enabled,
        "research_enabled": research_enabled,
        "stitch_enabled": stitch_enabled,
        "personal_project": personal_project,
        "pages_project_slug": (pages_project_slug or "").strip() or None,
        "project_title": (project_title or "").strip() or None,
        "fix_loops": 0,
        "autofix_attempts": 0,
        "testpilot_refix_loops": 0,
        "playwright_autofix_loops": 0,
        "lighthouse_autofix_loops": 0,
        "builder_fallback": True,
    }
    graph = get_compiled_pipeline()
    pid = (project_id or "").strip() or None
    try:
        final = await graph.ainvoke(
            initial,
            config={
                "configurable": {
                    "settings": resolved_settings,
                    "on_event": on_event,
                    "pipeline_started": pipeline_started,
                }
            },
        )

        if final.get("error"):
            raise ValueError(final["error"])

        result = final.get("result")
        if not result:
            raise ValueError("Le pipeline n'a pas produit de résultat.")
        return result
    finally:
        if pid:
            try:
                flush_project_costs(pid)
            except Exception:
                logger.exception("flush_project_costs(%s) échoué", pid)
