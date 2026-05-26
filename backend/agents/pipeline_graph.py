"""
Pipeline LangGraph complet — ArchitectAI → … → TestPilotAI → ExportAI → Finalisation.
ExportAI déploie sur Cloudflare Pages, Railway ou GitHub selon le type de projet.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Any, Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph

from agents.architect_agent import ArchitectAgent, ArchitectPlan
from agents.builder_agent import BuilderAgent, BuilderProvider
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
from config import Settings, get_settings
from tools.codegen_service import CodeGenComplexity, CodeGenService
from tools.demo_pipeline import build_client_demo_document
from tools.demo_template_service import (
    DemoSeedData,
    DemoTemplateService,
    TEMPLATE_LABELS,
    align_seed_template,
)
from tools.pricing import estimate_cost_usd
from tools.demo_template_service import TEMPLATE_MODEL, TEMPLATE_PROVIDER

logger = logging.getLogger(__name__)

MAX_AUTOFIX_LOOPS = 2
MAX_TESTPILOT_AUTOFIX_LOOPS = 1

PipelineEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

AGENT_LABELS: dict[str, str] = {
    "architect": "ArchitectAI",
    "builder": "BuilderAI",
    "coremind": "CoreMindAI",
    "visionui": "VisionUI",
    "bughunter": "BugHunterAI",
    "autofix": "AutoFixAI",
    "testpilot": "TestPilotAI",
    "export": "ExportAI",
    "finalize": "Finalisation",
}


class PipelineState(TypedDict, total=False):
    prompt: str
    project_type_hint: ProjectType | None
    architect_plan: ArchitectPlan | None
    analysis: CoreMindAnalysis | None
    builder_provider: str | None
    builder_fallback: bool
    generation: Any
    preview_html: str | None
    vision_screenshot_url: str | None
    vision_preview_source: str | None
    bug_report: BugHuntReport | None
    fix_loops: int
    autofix_attempts: int
    testpilot_report: Any
    testpilot_refix_loops: int
    validation_status: str | None
    export_result: Any
    result: CoreMindRunResult | None
    error: str | None


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


async def architect_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    await _step(cb, "architect", "start", "Analyse du prompt et choix du template…")
    settings = _settings_from_config(config)
    agent = ArchitectAgent(settings)
    plan, coremind_analysis = await agent.plan_with_analysis(
        state["prompt"],
        project_type_hint=state.get("project_type_hint"),
    )
    await _step(
        cb,
        "architect",
        "done",
        f"{plan.project_type_label} · template {plan.template_label}",
        template=plan.template,
        project_type=plan.project_type.value,
        used_llm=plan.used_llm,
    )
    return {
        "architect_plan": plan,
        "analysis": coremind_analysis,
    }


async def builder_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    plan = state.get("architect_plan")
    analysis = state.get("analysis")
    if not plan or not analysis:
        return {"error": "État pipeline incomplet (architect_plan manquant pour BuilderAI)."}

    await _step(cb, "builder", "start", "Routage v0 ou DeepSeek (ordres CoreMindAI)…")
    settings = _settings_from_config(config)
    agent = BuilderAgent(settings)
    result = await agent.build(
        state["prompt"],
        plan=plan,
        analysis=analysis,
        settings=settings,
    )
    provider_label = (
        "v0"
        if result.decision.provider == BuilderProvider.V0
        else "DeepSeek"
    )

    if result.fallback_to_coremind:
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

    await _step(
        cb,
        "builder",
        "done",
        f"Génération via {provider_label} réussie.",
        provider=result.decision.provider.value,
        fallback=False,
    )
    return {
        "builder_provider": result.decision.provider.value,
        "builder_fallback": False,
        "generation": result.generation,
        "preview_html": result.preview_html,
    }


def _route_after_builder(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if state.get("builder_fallback", True):
        return "coremind"
    if state.get("generation"):
        return "visionui"
    return "coremind"


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

    await _step(cb, "coremind", "start", "Génération HTML et seed adaptée au template…")
    settings = _settings_from_config(config)
    prompt = state["prompt"].strip()
    type_label = plan.project_type_label
    enriched = (
        f"Type de projet cible : {type_label}.\n"
        f"Template premium : {plan.template_label} ({plan.template}).\n\n{prompt}"
    )

    svc = DemoTemplateService(settings)
    seed: DemoSeedData = await svc.resolve_seed(
        enriched,
        project_type_label=type_label,
        template_hint=plan.template,
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

    html = (preview_html or "").strip()
    if not html and generation is not None:
        html = (getattr(generation, "code", None) or "").strip()

    if not html:
        await _step(cb, "visionui", "done", "Aucun HTML à capturer — étape ignorée.")
        return {}

    await _step(cb, "visionui", "start", "Capture visuelle du HTML généré…")
    settings = _settings_from_config(config)
    agent = VisionUIAgent(settings)
    result = await agent.capture(html, title=plan.project_type_label, settings=settings)
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
    cb = _callback_from_config(config)
    generation = state.get("generation")
    plan = state.get("architect_plan")
    if not generation or not plan:
        return {"error": "État pipeline incomplet (génération manquante)."}

    await _step(cb, "bughunter", "start", "Vérification du HTML généré…")
    settings = _settings_from_config(config)
    hunter = BugHunterAgent(settings)
    report = hunter.analyze_generation(
        generation,
        title=plan.project_type_label,
    )
    msg = (
        "Aucun problème détecté."
        if report.ok
        else f"{len(report.issues)} problème(s) : {', '.join(report.issue_codes[:6])}"
    )
    await _step(
        cb,
        "bughunter",
        "done",
        msg,
        ok=report.ok,
        issue_count=len(report.issues),
    )
    return {"bug_report": report}


def _route_after_bughunter(state: PipelineState) -> str:
    report = state.get("bug_report")
    if report and report.ok:
        return "testpilot"
    loops = state.get("fix_loops") or 0
    if loops >= MAX_AUTOFIX_LOOPS:
        return "testpilot"
    return "autofix"


async def autofix_node(
    state: PipelineState,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = _callback_from_config(config)
    report = state.get("bug_report")
    analysis = state.get("analysis")
    plan = state.get("architect_plan")
    if not report or not analysis or not plan:
        return {"error": "État pipeline incomplet (autofix)."}

    loop_num = (state.get("fix_loops") or 0) + 1
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
        return "export"
    refix = state.get("testpilot_refix_loops") or 0
    if refix > MAX_TESTPILOT_AUTOFIX_LOOPS:
        return "export"
    return "autofix"


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

    await _step(cb, "export", "start", "Déploiement automatique (Cloudflare / Railway / GitHub)…")
    settings = _settings_from_config(config)
    agent = ExportAgent(settings)
    preview_html = state.get("preview_html") or ""

    result = await agent.export(
        state["prompt"],
        plan=plan,
        analysis=analysis,
        generation=generation,
        preview_html=str(preview_html),
        settings=settings,
    )

    await _step(
        cb,
        "export",
        "done",
        result.message or "Export terminé.",
        ok=result.success,
        production_url=result.production_url,
        export_provider=result.provider,
        github_url=result.github_url,
        unlock_url=result.unlock_url,
    )
    return {"export_result": result}


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
    if export_data is not None:
        export_manifest = getattr(export_data, "manifest", None)
        production_url = getattr(export_data, "production_url", None)
        export_provider = getattr(export_data, "provider", None)
        github_export_url = getattr(export_data, "github_url", None)
        demo_token = getattr(export_data, "demo_token", None)
        demo_password = getattr(export_data, "demo_password", None)
        unlock_url = getattr(export_data, "unlock_url", None)

    result = CoreMindRunResult(
        analysis=analysis,
        generation=generation,
        metrics=metrics,
        planned_models=planned,
        demo_pipeline=pipeline_info,
        preview_html=preview_html,
        vision_screenshot_url=state.get("vision_screenshot_url"),
        vision_preview_source=state.get("vision_preview_source"),
        testpilot_passed=testpilot_passed,
        validation_status=validation_status,
        testpilot_summary=summary,
        export_manifest=export_manifest,
        production_url=production_url,
        export_provider=export_provider,
        github_export_url=github_export_url,
        demo_token=demo_token,
        demo_password=demo_password,
        unlock_url=unlock_url,
    )
    await _step(cb, "finalize", "done", "Génération terminée.")
    return {"result": result}


def build_pipeline_graph() -> Any:
    """Compile le graphe LangGraph."""
    graph = StateGraph(PipelineState)
    graph.add_node("architect", architect_node)
    graph.add_node("builder", builder_node)
    graph.add_node("coremind", coremind_node)
    graph.add_node("visionui", visionui_node)
    graph.add_node("bughunter", bughunter_node)
    graph.add_node("autofix", autofix_node)
    graph.add_node("testpilot", testpilot_node)
    graph.add_node("export", export_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("architect")
    graph.add_edge("architect", "builder")
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
        {"export": "export", "autofix": "autofix"},
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
    settings: Settings | None = None,
    on_event: PipelineEventCallback | None = None,
) -> CoreMindRunResult:
    """
    Exécute le pipeline complet et retourne le résultat CoreMindRunResult.
    Émet des événements step_* via on_event si fourni (SSE frontend).
    """
    resolved_settings = settings or get_settings()
    pipeline_started = time.perf_counter()
    initial: PipelineState = {
        "prompt": prompt.strip(),
        "project_type_hint": project_type_hint,
        "fix_loops": 0,
        "autofix_attempts": 0,
        "testpilot_refix_loops": 0,
        "builder_fallback": True,
    }
    graph = get_compiled_pipeline()
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
