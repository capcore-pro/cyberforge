"""
Pipeline CyberForge v2 — Brief → (DB/Auth/Payment) → Generator → Deploy.
SupervisorAI valide chaque étape et relance jusqu'à conformité (timeout 10 min / agent).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from agents.brief_ai import BriefAI
from agents.deploy_ai import DeployAI
from agents.generator_ai import GeneratorAI
from agents.supervisor_ai import SupervisorAI
from api.generation_stream import EXTENSION_TRACKED_TOTAL as _EXT_TOTAL
from api.generation_stream import TRACKED_TOTAL, generation_event_store
from db.supabase_store import SupabaseStoreError, get_supabase_store

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 600


def _apply_stripe_publishable_key(brief: dict[str, Any], stripe_publishable_key: str | None) -> None:
    """Transmet la clé publishable client au brief (sans journaliser la valeur)."""
    pk = (stripe_publishable_key or "").strip()
    if not pk:
        pc = brief.get("payment_config")
        if isinstance(pc, dict):
            pc["publishable_key"] = None
        return
    pc = brief.get("payment_config")
    if not isinstance(pc, dict):
        pc = {}
        brief["payment_config"] = pc
    pc["publishable_key"] = pk


class PipelineRequest(BaseModel):
    prompt: str = Field(min_length=3)
    project_type: str = "vitrine_next"
    client_name: str = ""
    generation_mode: str | None = None
    inspiration_brief: str | None = None
    firecrawl_result: dict[str, Any] | None = None
    stripe_publishable_key: str | None = None


def _print_supervisor_fail(agent_name: str, errors: list[str]) -> None:
    print(f"[SupervisorAI] ❌ {agent_name} invalide — erreurs: {errors}")


def _print_supervisor_retry(agent_name: str, attempt: int) -> None:
    print(f"[SupervisorAI] 🔄 {agent_name} relancé — tentative {attempt}")


async def _emit(
    generation_id: str | None,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    if not generation_id:
        return
    await generation_event_store.emit(generation_id, event_type, data)


async def _emit_log(generation_id: str | None, message: str) -> None:
    if not generation_id:
        return
    await generation_event_store.emit_log(generation_id, message)


async def _emit_agent_start(
    generation_id: str | None,
    *,
    agent: str,
    step: int,
    total: int | None = None,
) -> None:
    await _emit(
        generation_id,
        "agent_start",
        {"agent": agent, "step": step, "total": total if total is not None else TRACKED_TOTAL},
    )


async def _emit_agent_done(
    generation_id: str | None,
    *,
    agent: str,
    step: int,
    duration_ms: int,
    total: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "agent": agent,
        "step": step,
        "duration_ms": duration_ms,
    }
    if total is not None:
        payload["total"] = total
    await _emit(generation_id, "agent_done", payload)


async def _emit_agent_retry(
    generation_id: str | None,
    *,
    agent: str,
    attempt: int,
    reason: str,
) -> None:
    await _emit(
        generation_id,
        "agent_retry",
        {"agent": agent, "attempt": attempt, "reason": reason},
    )


async def _run_supervised(
    agent_name: str,
    run_once: Callable[[str], Awaitable[Any]],
    validate: Callable[[Any], Awaitable[dict[str, Any]]],
    *,
    initial_prompt: str,
    success_log: Callable[[Any], str] | None = None,
    generation_id: str | None = None,
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
                    msg = f"[SupervisorAI] ✅ {agent_name} validé — {success_log(last_result)}"
                    print(msg)
                    await _emit_log(generation_id, msg)
                return last_result

            errors = list(check.get("errors") or [])
            _print_supervisor_fail(agent_name, errors)
            reason = "; ".join(str(e) for e in errors) or "validation échouée"
            await _emit_log(
                generation_id,
                f"[SupervisorAI] {agent_name} invalide — {reason}",
            )
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


async def run_pipeline(
    request: PipelineRequest | dict[str, Any],
    *,
    generation_id: str | None = None,
) -> dict[str, Any]:
    pipeline_t0 = time.perf_counter()

    if isinstance(request, dict):
        req = PipelineRequest.model_validate(request)
    else:
        req = request

    try:
        return await _run_pipeline_body(req, generation_id=generation_id, pipeline_t0=pipeline_t0)
    except Exception as exc:
        await _emit(generation_id, "error", {"message": str(exc)})
        raise


async def _run_pipeline_body(
    req: PipelineRequest,
    *,
    generation_id: str | None,
    pipeline_t0: float,
) -> dict[str, Any]:
    supervisor = SupervisorAI()
    brief_ai = BriefAI()
    is_extension = (req.project_type or "").strip().lower() == "extension_navigateur"
    tracked_total = _EXT_TOTAL if is_extension else TRACKED_TOTAL

    async def _run_brief(prompt: str) -> dict[str, Any]:
        return await brief_ai.run(
            prompt=prompt,
            project_type=req.project_type,
            client_name=req.client_name,
        )

    async def _validate_brief(brief: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_brief(brief)

    await _emit_agent_start(
        generation_id, agent="BriefAI", step=1, total=tracked_total
    )
    brief_t0 = time.perf_counter()
    brief = await _run_supervised(
        "BriefAI",
        _run_brief,
        _validate_brief,
        initial_prompt=req.prompt,
        success_log=lambda b: f"client: {b.get('client_name', '?')}",
        generation_id=generation_id,
    )
    await _emit_agent_done(
        generation_id,
        agent="BriefAI",
        step=1,
        duration_ms=int((time.perf_counter() - brief_t0) * 1000),
        total=tracked_total,
    )

    brief["prompt"] = req.prompt
    if req.generation_mode:
        brief["generation_mode"] = req.generation_mode.strip()
    if req.inspiration_brief:
        brief["inspiration_brief"] = req.inspiration_brief.strip()
    if req.firecrawl_result:
        brief["firecrawl_result"] = req.firecrawl_result

    pt = (brief.get("project_type") or req.project_type or "").strip().lower()

    if pt == "extension_navigateur":
        return await _run_extension_pipeline(
            req,
            brief,
            generation_id=generation_id,
            pipeline_t0=pipeline_t0,
        )

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

        await _emit_log(generation_id, "DatabaseAI — schéma base de données")
        brief["database_schema"] = await _run_supervised(
            "DatabaseAI",
            _run_db,
            _validate_db,
            initial_prompt=base_desc,
            success_log=lambda s: f"{len((s or {}).get('tables') or [])} table(s)",
            generation_id=generation_id,
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

        await _emit_log(generation_id, "AuthAI — schéma authentification")
        brief["auth_schema"] = await _run_supervised(
            "AuthAI",
            _run_auth,
            _validate_auth,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda s: f"auth_type={s.get('auth_type', '?')}",
            generation_id=generation_id,
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

        await _emit_log(generation_id, "PaymentAI — configuration paiement")
        brief["payment_config"] = await _run_supervised(
            "PaymentAI",
            _run_payment,
            _validate_payment,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda p: f"type={p.get('payment_type', '?')}",
            generation_id=generation_id,
        )

    _apply_stripe_publishable_key(brief, req.stripe_publishable_key)

    generator = GeneratorAI()

    await _emit_agent_start(generation_id, agent="GeneratorAI", step=2)
    gen_t0 = time.perf_counter()
    correction = ""
    result: dict[str, Any] = {}

    async def _run_generator_once() -> dict[str, Any]:
        fixes = correction.strip() or None
        return await generator.run(brief, corrections=fixes)

    result = await _run_generator_once()
    await _emit_agent_done(
        generation_id,
        agent="GeneratorAI",
        step=2,
        duration_ms=int((time.perf_counter() - gen_t0) * 1000),
    )

    await _emit_agent_start(generation_id, agent="SupervisorAI", step=3)
    sup_t0 = time.perf_counter()

    async def _supervisor_html_loop() -> None:
        nonlocal result, correction
        attempt = 0
        while True:
            attempt += 1
            html = str((result or {}).get("html") or "")
            check = await supervisor.validate_html(html, brief)
            if check.get("valid"):
                msg = f"[SupervisorAI] ✅ HTML validé — {len(html)} car."
                print(msg)
                await _emit_log(generation_id, msg)
                return

            errors = list(check.get("errors") or [])
            _print_supervisor_fail("SupervisorAI", errors)
            reason = "; ".join(str(e) for e in errors) or "HTML invalide"
            await _emit_agent_retry(
                generation_id,
                agent="SupervisorAI",
                attempt=attempt,
                reason=reason,
            )
            corrected = str(check.get("corrected_prompt") or "").strip()
            correction = corrected
            _print_supervisor_retry("SupervisorAI", attempt + 1)
            gen_retry_t0 = time.perf_counter()
            result = await generator.run(brief, corrections=correction or None)
            await _emit_log(
                generation_id,
                f"GeneratorAI — regénération après rejet ({int((time.perf_counter() - gen_retry_t0) * 1000)} ms)",
            )

    await asyncio.wait_for(_supervisor_html_loop(), timeout=AGENT_TIMEOUT_SECONDS)
    await _emit_agent_done(
        generation_id,
        agent="SupervisorAI",
        step=3,
        duration_ms=int((time.perf_counter() - sup_t0) * 1000),
    )

    if not result.get("success") or not result.get("html"):
        error_msg = "GeneratorAI n'a pas produit de HTML valide."
        await _emit(generation_id, "error", {"message": error_msg})
        return {
            "url": "",
            "html": "",
            "success": False,
            "brief": brief,
            "error": error_msg,
        }

    deploy_ai = DeployAI()
    client_name = str(brief.get("client_name") or req.client_name or "CyberForge")
    sector = str(brief.get("sector") or "")
    html_in = str(result["html"])

    payment_config = brief.get("payment_config")
    if not isinstance(payment_config, dict):
        payment_config = None

    async def _run_deploy(_prompt: str) -> dict[str, Any]:
        return await deploy_ai.run(
            html_in,
            title=client_name,
            sector=sector,
            project_type=str(brief.get("project_type") or req.project_type or "vitrine_next"),
            payment_config=payment_config,
        )

    async def _validate_deploy(deployed: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_deployment(
            str(deployed.get("url") or ""),
            client_name,
        )

    await _emit_agent_start(generation_id, agent="DeployAI", step=4)
    deploy_t0 = time.perf_counter()
    deployed = await _run_supervised(
        "DeployAI",
        _run_deploy,
        _validate_deploy,
        initial_prompt="",
        success_log=lambda d: f"URL: {d.get('url', '')}",
        generation_id=generation_id,
    )
    await _emit_agent_done(
        generation_id,
        agent="DeployAI",
        step=4,
        duration_ms=int((time.perf_counter() - deploy_t0) * 1000),
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

    total_duration_ms = int((time.perf_counter() - pipeline_t0) * 1000)
    final_result = {
        "url": deployed.get("url", ""),
        "html": deployed.get("html") or result["html"],
        "success": bool(deployed.get("success")),
        "brief": brief,
        "unlock_url": deployed.get("unlock_url"),
        "demo_token": deployed.get("demo_token"),
        "demo_password": deployed.get("demo_password"),
        "error": deployed.get("error"),
        "duration_ms": total_duration_ms,
    }

    if final_result["success"]:
        await _emit(
            generation_id,
            "done",
            {
                "url": str(final_result.get("url") or ""),
                "html": str(final_result.get("html") or ""),
                "duration_ms": total_duration_ms,
                "unlock_url": final_result.get("unlock_url"),
                "demo_token": final_result.get("demo_token"),
                "demo_password": final_result.get("demo_password"),
            },
        )
    else:
        await _emit(
            generation_id,
            "error",
            {"message": str(final_result.get("error") or "Déploiement échoué")},
        )

    return final_result


async def _run_extension_pipeline(
    req: PipelineRequest,
    brief: dict[str, Any],
    *,
    generation_id: str | None,
    pipeline_t0: float,
) -> dict[str, Any]:
    """BriefAI → ExtensionBuilder → DeployAI (pas Generator/DB/Auth/Payment)."""
    from tools.extension_pipeline import build_extension_files, build_extension_zip

    supervisor = SupervisorAI()
    client_name = str(brief.get("client_name") or req.client_name or "CyberForge")
    primary_color = str(brief.get("couleur_primaire") or "#4f46e5")

    await _emit_agent_start(
        generation_id,
        agent="ExtensionBuilder",
        step=2,
        total=_EXT_TOTAL,
    )
    ext_t0 = time.perf_counter()
    await _emit_log(generation_id, "ExtensionBuilder — génération MV3")

    def _build() -> tuple[dict[str, str], bytes]:
        files = build_extension_files(brief)
        zip_bytes = build_extension_zip(files)
        return files, zip_bytes

    extension_files, zip_bytes = await asyncio.to_thread(_build)
    brief["extension_files"] = extension_files
    duration_ext = int((time.perf_counter() - ext_t0) * 1000)
    await _emit(
        generation_id,
        "agent_done",
        {
            "agent": "ExtensionBuilder",
            "step": 2,
            "duration_ms": duration_ext,
            "total": _EXT_TOTAL,
        },
    )
    await _emit_log(
        generation_id,
        f"ExtensionBuilder — {len(extension_files)} fichier(s), ZIP {len(zip_bytes)} octets",
    )

    deploy_ai = DeployAI()

    async def _run_deploy(_prompt: str) -> dict[str, Any]:
        del _prompt
        return await deploy_ai.run_extension(
            zip_bytes,
            extension_name=client_name,
            client_name=client_name,
            primary_color=primary_color,
            project_type="extension_navigateur",
        )

    async def _validate_deploy(deployed: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_deployment(
            str(deployed.get("url") or ""),
            client_name,
        )

    await _emit_agent_start(
        generation_id, agent="DeployAI", step=3, total=_EXT_TOTAL
    )
    deploy_t0 = time.perf_counter()
    deployed = await _run_supervised(
        "DeployAI",
        _run_deploy,
        _validate_deploy,
        initial_prompt="",
        success_log=lambda d: f"URL: {d.get('url', '')}",
        generation_id=generation_id,
    )
    await _emit(
        generation_id,
        "agent_done",
        {
            "agent": "DeployAI",
            "step": 3,
            "duration_ms": int((time.perf_counter() - deploy_t0) * 1000),
            "total": _EXT_TOTAL,
        },
    )

    deploy_url = str(deployed.get("url") or "")
    if deployed.get("success") and deploy_url:
        store = get_supabase_store()
        if store.is_configured():
            try:
                await store.save_pipeline_v2_deploy(
                    prompt=req.prompt,
                    project_type="extension_navigateur",
                    client_name=client_name,
                    demo_url=deploy_url,
                    html=str(deployed.get("html") or ""),
                )
            except SupabaseStoreError as exc:
                logger.warning("[pipeline] persistance Supabase ignorée: %s", exc)

    total_duration_ms = int((time.perf_counter() - pipeline_t0) * 1000)
    final_result = {
        "url": deployed.get("url", ""),
        "html": deployed.get("html") or "",
        "success": bool(deployed.get("success")),
        "brief": brief,
        "extension_zip_bytes": len(zip_bytes),
        "unlock_url": deployed.get("unlock_url"),
        "demo_token": deployed.get("demo_token"),
        "demo_password": deployed.get("demo_password") or "",
        "error": deployed.get("error"),
        "duration_ms": total_duration_ms,
    }

    if final_result["success"]:
        await _emit(
            generation_id,
            "done",
            {
                "url": str(final_result.get("url") or ""),
                "html": str(final_result.get("html") or ""),
                "duration_ms": total_duration_ms,
                "unlock_url": final_result.get("unlock_url"),
                "demo_token": final_result.get("demo_token"),
                "demo_password": final_result.get("demo_password"),
            },
        )
    else:
        await _emit(
            generation_id,
            "error",
            {"message": str(final_result.get("error") or "Déploiement extension échoué")},
        )

    return final_result
