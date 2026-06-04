"""
Pipeline CyberForge v2 — Brief → (DB/Auth/Payment) → Generator → Deploy.
SupervisorAI valide chaque étape et relance jusqu'à conformité (timeout 10 min / agent).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from agents.brief_ai import BriefAI
from agents.deploy_ai import DeployAI
from agents.generator_ai import GeneratorAI
from agents.supervisor_ai import SupervisorAI
from db.supabase_store import SupabaseStoreError, get_supabase_store

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 600


class PipelineRequest(BaseModel):
    prompt: str = Field(min_length=3)
    project_type: str = "vitrine_next"
    client_name: str = ""
    generation_mode: str | None = None
    inspiration_brief: str | None = None
    firecrawl_result: dict[str, Any] | None = None


def _print_supervisor_fail(agent_name: str, errors: list[str]) -> None:
    print(f"[SupervisorAI] ❌ {agent_name} invalide — erreurs: {errors}")


def _print_supervisor_retry(agent_name: str, attempt: int) -> None:
    print(f"[SupervisorAI] 🔄 {agent_name} relancé — tentative {attempt}")


async def _run_supervised(
    agent_name: str,
    run_once: Callable[[str], Awaitable[Any]],
    validate: Callable[[Any], Awaitable[dict[str, Any]]],
    *,
    initial_prompt: str,
    success_log: Callable[[Any], str] | None = None,
) -> Any:
    """
    Exécute run_once(prompt) jusqu'à validation SupervisorAI ou timeout 10 min.
    """
    supervisor = SupervisorAI()
    prompt = (initial_prompt or "").strip()
    attempt = 0

    async def _loop() -> Any:
        nonlocal prompt, attempt
        last_result: Any = None
        while True:
            attempt += 1
            last_result = await run_once(prompt)
            check = await validate(last_result)
            if check.get("valid"):
                if success_log:
                    print(f"[SupervisorAI] ✅ {agent_name} validé — {success_log(last_result)}")
                return last_result

            errors = list(check.get("errors") or [])
            _print_supervisor_fail(agent_name, errors)
            corrected = str(check.get("corrected_prompt") or "").strip()
            if corrected:
                prompt = corrected
            _print_supervisor_retry(agent_name, attempt + 1)

    try:
        return await asyncio.wait_for(_loop(), timeout=AGENT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(
            f"{agent_name} : timeout {AGENT_TIMEOUT_SECONDS}s dépassé après {attempt} tentative(s)"
        ) from exc


async def run_pipeline(request: PipelineRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, dict):
        req = PipelineRequest.model_validate(request)
    else:
        req = request

    supervisor = SupervisorAI()
    brief_ai = BriefAI()

    async def _run_brief(prompt: str) -> dict[str, Any]:
        return await brief_ai.run(
            prompt=prompt,
            project_type=req.project_type,
            client_name=req.client_name,
        )

    async def _validate_brief(brief: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_brief(brief)

    brief = await _run_supervised(
        "BriefAI",
        _run_brief,
        _validate_brief,
        initial_prompt=req.prompt,
        success_log=lambda b: f"client: {b.get('client_name', '?')}",
    )
    brief["prompt"] = req.prompt
    if req.generation_mode:
        brief["generation_mode"] = req.generation_mode.strip()
    if req.inspiration_brief:
        brief["inspiration_brief"] = req.inspiration_brief.strip()
    if req.firecrawl_result:
        brief["firecrawl_result"] = req.firecrawl_result

    pt = (brief.get("project_type") or req.project_type or "").strip().lower()

    if pt not in ("vitrine_next",):
        from agents import database_ai

        base_desc = str(brief.get("description") or req.prompt)

        async def _run_db(prompt: str) -> dict[str, Any]:
            return await database_ai.run(
                project_description=prompt,
                project_type=pt,
                design_system={},
            )

        async def _validate_db(schema: dict[str, Any]) -> dict[str, Any]:
            return await supervisor.validate_database(schema, brief)

        brief["database_schema"] = await _run_supervised(
            "DatabaseAI",
            _run_db,
            _validate_db,
            initial_prompt=base_desc,
            success_log=lambda s: f"{len((s or {}).get('tables') or [])} table(s)",
        )

    if pt in ("application_web", "real_app"):
        from agents import auth_ai

        async def _run_auth(prompt: str) -> dict[str, Any]:
            return await auth_ai.run(
                project_description=prompt,
                project_type=pt,
                database_schema=brief.get("database_schema") or {},
            )

        async def _validate_auth(_schema: dict[str, Any]) -> dict[str, Any]:
            if isinstance(_schema, dict) and _schema.get("auth_type"):
                return {"valid": True, "errors": [], "corrected_prompt": ""}
            return {
                "valid": False,
                "errors": ["auth_schema vide ou auth_type manquant"],
                "corrected_prompt": str(brief.get("description") or req.prompt),
            }

        brief["auth_schema"] = await _run_supervised(
            "AuthAI",
            _run_auth,
            _validate_auth,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda s: f"auth_type={s.get('auth_type', '?')}",
        )

    if pt in ("ecommerce", "site_reservation"):
        from agents import payment_ai

        async def _run_payment(prompt: str) -> dict[str, Any]:
            return await payment_ai.run(
                project_description=prompt,
                project_type=pt,
                database_schema=brief.get("database_schema") or {},
            )

        async def _validate_payment(payment: dict[str, Any]) -> dict[str, Any]:
            return await supervisor.validate_payment(payment, brief)

        brief["payment_config"] = await _run_supervised(
            "PaymentAI",
            _run_payment,
            _validate_payment,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda p: f"type={p.get('payment_type', '?')}",
        )

    generator = GeneratorAI()

    async def _run_generator(correction: str) -> dict[str, Any]:
        fixes = correction.strip() or None
        return await generator.run(brief, corrections=fixes)

    async def _validate_generator(result: dict[str, Any]) -> dict[str, Any]:
        html = str((result or {}).get("html") or "")
        return await supervisor.validate_html(html, brief)

    result = await _run_supervised(
        "GeneratorAI",
        _run_generator,
        _validate_generator,
        initial_prompt="",
        success_log=lambda r: (
            f"client: {brief.get('client_name')} — {len(str(r.get('html') or ''))} car."
        ),
    )

    if not result.get("success") or not result.get("html"):
        return {
            "url": "",
            "html": "",
            "success": False,
            "brief": brief,
            "error": "GeneratorAI n'a pas produit de HTML valide.",
        }

    deploy_ai = DeployAI()
    client_name = str(brief.get("client_name") or req.client_name or "CyberForge")
    sector = str(brief.get("sector") or "")
    html_in = str(result["html"])

    async def _run_deploy(_prompt: str) -> dict[str, Any]:
        return await deploy_ai.run(
            html_in,
            title=client_name,
            sector=sector,
            project_type=str(brief.get("project_type") or req.project_type or "vitrine_next"),
        )

    async def _validate_deploy(deployed: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_deployment(
            str(deployed.get("url") or ""),
            client_name,
        )

    deployed = await _run_supervised(
        "DeployAI",
        _run_deploy,
        _validate_deploy,
        initial_prompt="",
        success_log=lambda d: f"URL: {d.get('url', '')}",
    )

    deploy_url = str(deployed.get("url") or "")
    if deployed.get("success") and deploy_url:
        store = get_supabase_store()
        if store.is_configured():
            try:
                await store.save_pipeline_v2_deploy(
                    prompt=req.prompt,
                    project_type=str(
                        brief.get("project_type") or req.project_type or "vitrine_next"
                    ),
                    client_name=client_name,
                    demo_url=deploy_url,
                    html=str(deployed.get("html") or result.get("html") or ""),
                )
            except SupabaseStoreError as exc:
                logger.warning("[pipeline] persistance Supabase ignorée: %s", exc)

    return {
        "url": deployed.get("url", ""),
        "html": deployed.get("html") or result["html"],
        "success": bool(deployed.get("success")),
        "brief": brief,
        "unlock_url": deployed.get("unlock_url"),
        "demo_token": deployed.get("demo_token"),
        "demo_password": deployed.get("demo_password"),
        "error": deployed.get("error"),
    }
