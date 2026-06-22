"""
Routage LangGraph et symboles partagés du pipeline de génération.

Extrait pour permettre les imports depuis pipeline_graph.py sans charger
tout le graphe LangGraph (agents optionnels, nodes async, etc.).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from agents.coremind_agent import CoreMindAnalysis, CoreMindRunResult, ProjectType
from agents.openhands_agent import OpenHandsAgent, openhands_eligible
from config import get_settings

MAX_AUTOFIX_LOOPS = 2
MAX_TESTPILOT_AUTOFIX_LOOPS = 1

DIRECT_COREMIND_MODES = frozenset({"real_app"})

NODE_DESIGN_SYSTEM = "design_system_ai"
NODE_DATABASE = "database_ai"

GENERATED_TEMPLATE_PRICING_CATEGORIES: frozenset[str] = frozenset(
    {"vitrine_next", "ecommerce", "site_reservation"}
)


class PipelineState(TypedDict, total=False):
    prompt: str
    inspiration_brief: str | None
    firecrawl_result: Any
    project_id: str | None
    project_type: str | None
    project_type_hint: ProjectType | None
    generation_mode: str | None
    openhands_enabled: bool | None
    playwright_enabled: bool | None
    lighthouse_enabled: bool | None
    research_enabled: bool | None
    architect_plan: Any
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
    bug_report: Any
    fix_loops: int
    autofix_attempts: int
    testpilot_report: Any
    testpilot_refix_loops: int
    playwright_report: Any
    playwright_autofix_loops: int
    lighthouse_report: Any
    lighthouse_autofix_loops: int
    research_brief: Any
    validation_status: str | None
    personal_project: bool | None
    pages_project_slug: str | None
    project_title: str | None
    project_name: str | None
    export_result: Any
    extension_files: dict[str, str] | None
    artifact_download_url: str | None
    result: CoreMindRunResult | None
    error: str | None
    database_schema: Any
    auth_schema: Any
    electron_files: Any
    payment_config: Any


def _should_run_database_ai(state: PipelineState) -> bool:
    pt = (state.get("project_type") or "").strip().lower()
    if not pt:
        return False
    return pt not in ("vitrine_next", "extension_navigateur")


def _research_requested(state: PipelineState) -> bool:
    if state.get("research_enabled") is False:
        return False
    return get_settings().research_enabled


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


def _should_use_template_generator(state: PipelineState) -> bool:
    plan = state.get("architect_plan")
    if not plan:
        return False
    cat = (getattr(plan, "pricing_category", None) or "").strip().lower()
    return cat in GENERATED_TEMPLATE_PRICING_CATEGORIES


def _playwright_requested(state: PipelineState) -> bool:
    if state.get("playwright_enabled") is False:
        return False
    return get_settings().playwright_enabled


def _lighthouse_requested(state: PipelineState) -> bool:
    if state.get("lighthouse_enabled") is False:
        return False
    return get_settings().lighthouse_enabled


def _route_after_architect(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if _should_run_database_ai(state):
        return NODE_DATABASE
    if _openhands_requested(state):
        return "openhands"
    mode = (state.get("generation_mode") or "client_demo").strip().lower()
    if mode in DIRECT_COREMIND_MODES:
        return "coremind"
    if _research_requested(state):
        return "research"
    return NODE_DESIGN_SYSTEM


def _route_after_research(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return NODE_DESIGN_SYSTEM


def _route_after_template_ai(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return "content_ai"


def _route_after_builder(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    if state.get("builder_fallback", True):
        if _block_coremind_builder_fallback(state):
            if state.get("generation"):
                return "visionui"
            return "finalize"
        return "coremind"
    if state.get("generation"):
        return "visionui"
    return "coremind"


def _block_coremind_builder_fallback(state: PipelineState) -> bool:
    plan = state.get("architect_plan")
    if not plan:
        return False
    from agents.builder_agent import must_force_sector_template_assembly

    return must_force_sector_template_assembly(
        plan,
        sector_template_html=_sector_template_html_from_state(state),
        sector_template=state.get("sector_template"),
    )


def _sector_template_html_from_state(state: PipelineState) -> str | None:
    sector = state.get("sector_template")
    if sector is None:
        return None
    if isinstance(sector, str):
        return sector
    return getattr(sector, "html", None) or getattr(sector, "content", None)


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


def _route_after_playwright(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return "lighthouse" if _lighthouse_requested(state) else "export"


def _route_after_lighthouse(state: PipelineState) -> str:
    if state.get("error"):
        return "finalize"
    return "export"


def _inject_package_json(
    generation: Any,
    project_label: str,
    *,
    plan: Any = None,
) -> Any:
    """Ajoute package.json + src/main.tsx + index.html si absents."""
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
        if plan and getattr(plan, "palette", None):
            from tools.toolbox_branding import _merge_package_json

            pkg_content = _merge_package_json(pkg_content, plan)
        extra.append(GeneratedFile(path="package.json", content=pkg_content))

    if "index.html" not in existing_paths and "src/main.tsx" not in existing_paths:
        extra.append(
            GeneratedFile(
                path="index.html",
                content=(
                    '<!DOCTYPE html>\n<html lang="fr">\n  <head>\n'
                    '    <meta charset="UTF-8" />\n'
                    '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                    f"    <title>{project_label}</title>\n"
                    "  </head>\n  <body>\n    <div id=\"root\"></div>\n"
                    '    <script type="module" src="/src/main.tsx"></script>\n'
                    "  </body>\n</html>"
                ),
            )
        )
        extra.append(
            GeneratedFile(
                path="src/main.tsx",
                content=(
                    'import React from "react";\n'
                    'import ReactDOM from "react-dom/client";\n'
                    'import App from "./App";\n\n'
                    'ReactDOM.createRoot(document.getElementById("root")!).render(\n'
                    "  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n"
                ),
            )
        )

    if plan and getattr(plan, "palette", None) and "package.json" in existing_paths:
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
