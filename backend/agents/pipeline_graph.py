# backend/agents/pipeline_graph.py
# Façade de compatibilité — réexporte le routage, OpenHands et run_generation_pipeline.

from __future__ import annotations

from typing import Any

from agents.coremind_agent import CoreMindRunResult, ProjectType
from agents.openhands_agent import OpenHandsAgent
from config import Settings, get_settings

from .openhands_pipeline import run_debug_pipeline, run_openhands_pipeline
from .pipeline_graph_routing import (
    DIRECT_COREMIND_MODES,
    GENERATED_TEMPLATE_PRICING_CATEGORIES,
    MAX_AUTOFIX_LOOPS,
    MAX_TESTPILOT_AUTOFIX_LOOPS,
    NODE_DESIGN_SYSTEM,
    PipelineState,
    _inject_package_json,
    _lighthouse_requested,
    _openhands_requested,
    _playwright_requested,
    _research_requested,
    _route_after_architect,
    _route_after_builder,
    _route_after_bughunter,
    _route_after_lighthouse,
    _route_after_playwright,
    _route_after_research,
    _route_after_template_ai,
    _route_after_testpilot,
    _should_use_template_generator,
)

__all__ = [
    "DIRECT_COREMIND_MODES",
    "GENERATED_TEMPLATE_PRICING_CATEGORIES",
    "MAX_AUTOFIX_LOOPS",
    "MAX_TESTPILOT_AUTOFIX_LOOPS",
    "NODE_DESIGN_SYSTEM",
    "OpenHandsAgent",
    "PipelineState",
    "Settings",
    "get_settings",
    "_inject_package_json",
    "_lighthouse_requested",
    "_openhands_requested",
    "_playwright_requested",
    "_research_requested",
    "_route_after_architect",
    "_route_after_builder",
    "_route_after_bughunter",
    "_route_after_lighthouse",
    "_route_after_playwright",
    "_route_after_research",
    "_route_after_template_ai",
    "_route_after_testpilot",
    "_should_use_template_generator",
    "run_debug_pipeline",
    "run_generation_pipeline",
    "run_openhands_pipeline",
]


async def run_generation_pipeline(
    prompt: str,
    *,
    project_type_hint: ProjectType | None = None,
    generation_mode: str | None = None,
    openhands_enabled: bool | None = None,
    playwright_enabled: bool | None = None,
    lighthouse_enabled: bool | None = None,
    research_enabled: bool | None = None,
    project_id: str | None = None,
    inspiration_brief: str | None = None,
    firecrawl_result: dict[str, Any] | None = None,
    personal_project: bool = False,
    pages_project_slug: str | None = None,
    project_title: str | None = None,
    settings: Settings | None = None,
    on_event: Any = None,
) -> CoreMindRunResult:
    """Délègue au graphe LangGraph complet (chargement paresseux)."""
    from .pipeline_graph_core import run_generation_pipeline as _run

    return await _run(
        prompt,
        project_type_hint=project_type_hint,
        generation_mode=generation_mode,
        openhands_enabled=openhands_enabled,
        playwright_enabled=playwright_enabled,
        lighthouse_enabled=lighthouse_enabled,
        research_enabled=research_enabled,
        project_id=project_id,
        inspiration_brief=inspiration_brief,
        firecrawl_result=firecrawl_result,
        personal_project=personal_project,
        pages_project_slug=pages_project_slug,
        project_title=project_title,
        settings=settings,
        on_event=on_event,
    )
