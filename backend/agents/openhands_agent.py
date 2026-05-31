"""
OpenHandsAgent — génération de code avancée pour projets complexes (≥ 7/10).

Utilise le SDK OpenHands (Python ≥ 3.12) avec Claude Sonnet (ANTHROPIC_API_KEY).
Repli Anthropic direct si le SDK est indisponible ; repli DeepSeek en cas d'échec.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.coremind_agent import CoreMindAnalysis, ProjectType
from agents.demo_quality import preview_html_from_generation
from config import Settings
from cost_tracker import maybe_track_cost, usage_from_anthropic_payload
from prompts.openhands import OPENHANDS_ANTHROPIC_SYSTEM, OPENHANDS_TASK_TEMPLATE
from prompts import PERSONALIZED_CONTENT_DIRECTIVE
from security.llm_secrets import get_effective_llm_key, get_effective_llm_key_for_http
from tools.builder_generators import BuildOutcome, DeepSeekBuilderClient, _code_from_llm_text
from tools.codegen_service import CodeGenerateResult, GeneratedFile, _utf8_json_body
from tools.toolbox_branding import apply_toolbox_to_generation, build_toolbox_builder_context

logger = logging.getLogger(__name__)

OPENHANDS_SDK_AVAILABLE = False
if sys.version_info >= (3, 12):
    try:
        from openhands.sdk import Agent, Conversation, LLM, Tool  # noqa: F401
        from openhands.tools.file_editor import FileEditorTool  # noqa: F401
        from openhands.tools.task_tracker import TaskTrackerTool  # noqa: F401
        from openhands.tools.terminal import TerminalTool  # noqa: F401

        OPENHANDS_SDK_AVAILABLE = True
    except ImportError:
        pass

_SKIP_WORKSPACE_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", ".openhands"})


class OpenHandsRunResult(BaseModel):
    """Résultat d'exécution OpenHandsAgent — format aligné BuilderAI."""

    agent_id: str = "openhands"
    agent_name: str = "OpenHands"
    provider: str = "openhands"
    outcome: BuildOutcome | None = None
    fallback_to_coremind: bool = True
    generation: CodeGenerateResult | None = None
    preview_html: str | None = None


def openhands_eligible(
    *,
    plan: ArchitectPlan,
    generation_mode: str | None,
    enabled: bool = True,
    threshold: int = 7,
) -> bool:
    """Projets real_app ou application_web avec complexité ≥ seuil."""
    if not enabled:
        return False
    if plan.complexity_score < threshold:
        return False
    mode = (generation_mode or "client_demo").strip()
    if mode == "real_app":
        return True
    return plan.project_type == ProjectType.APPLICATION_WEB


class OpenHandsAgent(BaseAgent):
    """Agent OpenHands — Claude Sonnet, structure complète, repli DeepSeek."""

    @property
    def agent_id(self) -> str:
        return "openhands"

    @property
    def name(self) -> str:
        return "OpenHands"

    def is_configured(self) -> bool:
        return bool(get_effective_llm_key("ANTHROPIC_API_KEY", self._settings))

    async def run(self, prompt: str, **kwargs: Any) -> str:
        plan = kwargs.get("architect_plan")
        analysis = kwargs.get("analysis")
        if not isinstance(plan, ArchitectPlan) or not isinstance(analysis, CoreMindAnalysis):
            raise ValueError("architect_plan et analysis requis pour OpenHands")
        result = await self.build(
            prompt,
            plan=plan,
            analysis=analysis,
            settings=kwargs.get("settings"),
            project_id=kwargs.get("project_id"),
        )
        return result.model_dump_json()

    def _build_task_prompt(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
    ) -> str:
        toolbox_block = build_toolbox_builder_context(plan)
        task = OPENHANDS_TASK_TEMPLATE.format(
            project_type_label=plan.project_type_label,
            template_label=plan.template_label,
            complexity_label=plan.complexity_label,
            complexity_score=plan.complexity_score,
            rationale=plan.rationale.strip(),
            toolbox_block=toolbox_block,
            prompt=prompt.strip(),
        )
        return f"{PERSONALIZED_CONTENT_DIRECTIVE}\n\n{task}"

    async def build(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        settings: Settings | None = None,
        project_id: str | None = None,
    ) -> OpenHandsRunResult:
        resolved = settings or self._settings
        if not self.is_configured():
            return OpenHandsRunResult(
                provider="openhands",
                outcome=BuildOutcome(
                    provider="openhands",
                    success=False,
                    error="ANTHROPIC_API_KEY non configurée",
                ),
                fallback_to_coremind=True,
            )

        enriched = self._build_task_prompt(prompt, plan=plan)
        outcome: BuildOutcome | None = None

        if OPENHANDS_SDK_AVAILABLE and resolved.openhands_use_sdk:
            outcome = await self._generate_via_sdk(enriched, settings=resolved, project_id=project_id)
            if outcome.success:
                return self._success_result(outcome, plan, project_id=project_id)
            logger.warning(
                "OpenHands SDK échoué (%s) — repli Anthropic direct",
                outcome.error,
            )

        outcome = await self._generate_via_anthropic(enriched, settings=resolved, project_id=project_id)
        if outcome.success:
            return self._success_result(outcome, plan, project_id=project_id)

        logger.warning(
            "OpenHands Anthropic échoué (%s) — repli DeepSeek",
            outcome.error,
        )
        deepseek = await DeepSeekBuilderClient(resolved).generate_code(
            enriched,
            project_id=project_id,
        )
        if deepseek.success and deepseek.generation is not None:
            return self._success_result(
                BuildOutcome(
                    provider="deepseek",
                    success=True,
                    summary=deepseek.summary,
                    generation=deepseek.generation,
                ),
                plan,
                project_id=project_id,
                provider_label="deepseek",
            )

        error = deepseek.error or outcome.error or "OpenHands et DeepSeek indisponibles"
        return OpenHandsRunResult(
            provider="openhands",
            outcome=deepseek if not deepseek.success else outcome,
            fallback_to_coremind=True,
        )

    def _success_result(
        self,
        outcome: BuildOutcome,
        plan: ArchitectPlan,
        *,
        project_id: str | None,
        provider_label: str | None = None,
    ) -> OpenHandsRunResult:
        generation = apply_toolbox_to_generation(
            outcome.generation,
            plan,
            project_id=project_id,
        )
        preview_html = preview_html_from_generation(
            generation,
            title=plan.project_type_label,
            user_prompt=plan.rationale,
        )
        return OpenHandsRunResult(
            provider=provider_label or "openhands",
            outcome=outcome,
            fallback_to_coremind=False,
            generation=generation,
            preview_html=preview_html,
        )

    async def _generate_via_sdk(
        self,
        prompt: str,
        *,
        settings: Settings,
        project_id: str | None,
    ) -> BuildOutcome:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _run_openhands_sdk_sync,
                    prompt,
                    settings,
                    project_id,
                ),
                timeout=settings.openhands_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return BuildOutcome(
                provider="openhands",
                success=False,
                error=f"timeout OpenHands ({settings.openhands_timeout_seconds}s)",
            )
        except Exception as exc:
            logger.exception("OpenHands SDK")
            return BuildOutcome(provider="openhands", success=False, error=str(exc))

    async def _generate_via_anthropic(
        self,
        prompt: str,
        *,
        settings: Settings,
        project_id: str | None,
    ) -> BuildOutcome:
        api_key = get_effective_llm_key_for_http("ANTHROPIC_API_KEY", settings)
        if not api_key:
            return BuildOutcome(
                provider="anthropic",
                success=False,
                error="ANTHROPIC_API_KEY non configurée",
            )

        model = settings.coremind_sonnet_model
        body = {
            "model": model,
            "max_tokens": settings.openhands_max_output_tokens,
            "system": OPENHANDS_ANTHROPIC_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
        }
        body_bytes, content_headers = _utf8_json_body(body)
        timeout = httpx.Timeout(settings.openhands_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        **content_headers,
                    },
                    content=body_bytes,
                )
        except httpx.HTTPError as exc:
            return BuildOutcome(provider="anthropic", success=False, error=str(exc))

        if response.status_code >= 400:
            return BuildOutcome(
                provider="anthropic",
                success=False,
                error=f"HTTP {response.status_code}",
            )

        try:
            payload = response.json()
            blocks = payload.get("content", [])
            text = "".join(
                block.get("text", "") for block in blocks if block.get("type") == "text"
            )
            code, files = _code_from_llm_text(text, default_path="src/App.tsx")
            maybe_track_cost(
                project_id,
                "claude_sonnet",
                usage_from_anthropic_payload(payload),
            )
        except (ValueError, KeyError) as exc:
            return BuildOutcome(provider="anthropic", success=False, error=str(exc))

        generation = CodeGenerateResult(
            summary="Application générée via OpenHands (Claude Sonnet)",
            code=code,
            files=files,
            stack=["react", "typescript", "vite"],
            model=model,
            provider="openhands",
        )
        return BuildOutcome(
            provider="openhands",
            success=True,
            summary=generation.summary,
            generation=generation,
        )


def _run_openhands_sdk_sync(
    prompt: str,
    settings: Settings,
    project_id: str | None,
) -> BuildOutcome:
    from openhands.sdk import Agent, Conversation, LLM, Tool
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.task_tracker import TaskTrackerTool
    from openhands.tools.terminal import TerminalTool

    api_key = get_effective_llm_key("ANTHROPIC_API_KEY", settings)
    if not api_key:
        return BuildOutcome(
            provider="openhands",
            success=False,
            error="ANTHROPIC_API_KEY non configurée",
        )

    model = settings.coremind_sonnet_model
    litellm_model = model if "/" in model else f"anthropic/{model}"

    with tempfile.TemporaryDirectory(prefix="cf-openhands-") as workspace:
        llm = LLM(model=litellm_model, api_key=api_key)
        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
        )
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message(prompt)
        conversation.run()

        files = _collect_workspace_files(workspace)
        if not files:
            return BuildOutcome(
                provider="openhands",
                success=False,
                error="OpenHands SDK n'a produit aucun fichier",
            )

        primary = _pick_primary_file(files)
        generation = CodeGenerateResult(
            summary="Application générée via OpenHands SDK (Claude Sonnet)",
            code=primary.content,
            files=files,
            stack=["react", "typescript", "vite"],
            model=model,
            provider="openhands",
        )
        maybe_track_cost(project_id, "claude_sonnet", {"requests": 1})
        return BuildOutcome(
            provider="openhands",
            success=True,
            summary=generation.summary,
            generation=generation,
        )


def _collect_workspace_files(
    root: str,
    *,
    max_files: int = 80,
    max_bytes: int = 900_000,
) -> list[GeneratedFile]:
    collected: list[GeneratedFile] = []
    total = 0
    root_path = Path(root)

    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root_path).as_posix()
        if any(part in _SKIP_WORKSPACE_DIRS for part in path.parts):
            continue
        if path.name.startswith("."):
            continue
        try:
            if path.stat().st_size > 120_000:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        size = len(content.encode("utf-8"))
        if total + size > max_bytes or len(collected) >= max_files:
            break
        total += size
        collected.append(GeneratedFile(path=rel, content=content))
    return collected


def _pick_primary_file(files: list[GeneratedFile]) -> GeneratedFile:
    priority = (
        "src/App.tsx",
        "src/main.tsx",
        "app/page.tsx",
        "index.html",
    )
    by_path = {f.path: f for f in files}
    for path in priority:
        if path in by_path:
            return by_path[path]
    return files[0]
