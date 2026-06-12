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
from agents.design_system_ai import DesignSystemAgent
from agents.generator_ai import GeneratorAI
from agents.llm_usage_utils import pop_agent_usage
from agents.supervisor_ai import SupervisorAI
from llm.llm_usage_service import LLMUsageTotals, get_llm_usage_service
from api.generation_stream import EXTENSION_TRACKED_TOTAL as _EXT_TOTAL
from api.generation_stream import TRACKED_TOTAL, generation_event_store
from db.supabase_store import SupabaseStoreError, get_supabase_store

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 600
MAX_RETRIES = 3
MAX_HTML_RETRIES = 3


class MaxRetriesExceeded(Exception):
    """Le superviseur a épuisé le nombre maximal de tentatives autorisées."""


_AGENT_RECEIVER_SLUG: dict[str, str] = {
    "BriefAI": "brief_ai",
    "DatabaseAI": "database_ai",
    "AuthAI": "auth_ai",
    "PaymentAI": "payment_ai",
    "GeneratorAI": "generator_ai",
    "DeployAI": "deploy_ai",
    "SupervisorAI": "supervisor_ai",
}


_AGENT_PLAN_KEYS: dict[str, str] = {
    "BriefAI": "brief",
    "DesignSystemAI": "design_system",
    "DatabaseAI": "database",
    "AuthAI": "auth",
    "PaymentAI": "payment",
    "GeneratorAI": "generator",
    "SupervisorAI": "supervisor",
    "DeployAI": "deploy",
    "ExtensionBuilder": "extension_builder",
}


def _decision_type_for_agent(agent_name: str) -> str:
    mapping = {
        "BriefAI": "brief",
        "DatabaseAI": "database",
        "AuthAI": "auth",
        "PaymentAI": "payment",
        "DeployAI": "deployment",
        "SupervisorAI": "html",
    }
    return mapping.get(agent_name, agent_name.lower().replace("ai", ""))


def _schedule_supervisor_decision(**kwargs: Any) -> None:
    async def _record() -> None:
        from db.supervisor_store import get_supervisor_store

        await get_supervisor_store().record_decision(**kwargs)

    _schedule_audit(_record())


def _schedule_quality_review(**kwargs: Any) -> None:
    async def _record() -> None:
        from db.supervisor_store import get_supervisor_store

        await get_supervisor_store().record_quality_review(**kwargs)

    _schedule_audit(_record())


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


def _schedule_audit(coro: Awaitable[None]) -> None:
    """Audit non bloquant — ne doit jamais faire échouer le pipeline."""

    async def _runner() -> None:
        try:
            await coro
        except Exception as exc:
            logger.warning("[AuditStore] log ignoré — %s", exc)

    asyncio.create_task(_runner())


def _new_workflow_ctx() -> dict[str, Any]:
    return {
        "execution_id": None,
        "step_by_agent_name": {},
        "total_steps": 0,
    }


def _schedule_workflow(coro: Awaitable[None]) -> None:
    """Workflow store non bloquant — ne doit jamais faire échouer le pipeline."""

    async def _runner() -> None:
        try:
            await coro
        except Exception as exc:
            logger.warning("[WorkflowStore] ignoré — %s", exc)

    asyncio.create_task(_runner())


def _schedule_orchestration(coro: Awaitable[None]) -> None:
    """Orchestration store non bloquant — ne doit jamais faire échouer le pipeline."""

    async def _runner() -> None:
        try:
            await coro
        except Exception as exc:
            logger.warning("[OrchestrationStore] ignoré — %s", exc)

    asyncio.create_task(_runner())


def _track_orchestration_agent(
    orchestration_ctx: dict[str, Any],
    agent_name: str,
    *,
    generation_id: str | None,
) -> None:
    plan_key = _AGENT_PLAN_KEYS.get(agent_name, agent_name.lower())
    completed: list[str] = orchestration_ctx.setdefault("agents_completed", [])
    if plan_key not in completed:
        completed.append(plan_key)
    if not generation_id:
        return
    _schedule_orchestration(
        _orchestration_update_session(generation_id, orchestration_ctx, current_agent=plan_key)
    )


async def _orchestration_update_session(
    generation_id: str,
    orchestration_ctx: dict[str, Any],
    *,
    current_agent: str | None = None,
    parallel_groups: list[list[str]] | None = None,
) -> None:
    from db.orchestration_store import get_orchestration_store

    await get_orchestration_store().update_session(
        generation_id,
        status="running",
        agents_completed=list(orchestration_ctx.get("agents_completed") or []),
        agents_failed=list(orchestration_ctx.get("agents_failed") or []),
        current_agent=current_agent,
        parallel_groups=parallel_groups,
    )


def _orchestration_complete(
    orchestration_ctx: dict[str, Any],
    generation_id: str | None,
) -> None:
    if not orchestration_ctx.get("session_id") or not generation_id:
        return
    status = str(orchestration_ctx.get("status") or "completed")
    _schedule_orchestration(
        _orchestration_finish_session(generation_id, status)
    )


async def _orchestration_finish_session(generation_id: str, status: str) -> None:
    from db.orchestration_store import get_orchestration_store

    await get_orchestration_store().complete_session(generation_id, status=status)


async def _orchestration_set_brief_context(session_id: str, brief: dict[str, Any]) -> None:
    from db.orchestration_store import get_orchestration_store

    await get_orchestration_store().set_shared_context(
        session_id=session_id,
        context_key="brief",
        context_value=brief,
        produced_by="brief_ai",
    )


async def _orchestration_set_html_context(
    session_id: str,
    html_length: int,
    quality_score: int,
) -> None:
    from db.orchestration_store import get_orchestration_store

    await get_orchestration_store().set_shared_context(
        session_id=session_id,
        context_key="html",
        context_value={"length": html_length, "quality_score": quality_score},
        produced_by="generator_ai",
    )


async def _workflow_init(
    ctx: dict[str, Any],
    *,
    generation_id: str | None,
    brief: dict[str, Any],
    project_type: str,
) -> None:
    if not generation_id:
        return
    from db.workflow_store import get_workflow_store

    store = get_workflow_store()
    if not store.is_configured():
        return

    workflow = await store.get_workflow_for_project_type(project_type)
    if not workflow:
        return

    workflow_uuid = str(workflow.get("id") or "")
    if not workflow_uuid:
        return

    steps = await store.get_steps(workflow_uuid)
    ctx["total_steps"] = len(steps)
    ctx["step_by_agent_name"] = {
        str(step.get("step_name") or ""): int(step.get("execution_order") or 0)
        for step in steps
        if step.get("step_name")
    }

    execution = await store.create_execution(
        workflow_uuid,
        generation_id,
        project_id=str(brief.get("project_id") or "") or None,
        total_steps=len(steps),
    )
    execution_id = str(execution.get("id") or "")
    if not execution_id:
        return

    ctx["execution_id"] = execution_id
    await store.update_execution(
        execution_id,
        current_step="BriefAI",
        completed_steps=ctx["step_by_agent_name"].get("BriefAI", 1),
    )


async def _workflow_step_done(ctx: dict[str, Any], agent_name: str) -> None:
    execution_id = ctx.get("execution_id")
    if not execution_id:
        return

    step_number = (ctx.get("step_by_agent_name") or {}).get(agent_name)
    if not step_number:
        return

    from db.workflow_store import get_workflow_store

    await get_workflow_store().update_execution(
        str(execution_id),
        current_step=agent_name,
        completed_steps=int(step_number),
    )


async def _workflow_complete(
    ctx: dict[str, Any],
    *,
    status: str,
    total_cost_usd: float = 0,
    total_tokens: int = 0,
    duration_ms: int = 0,
    error_message: str | None = None,
) -> None:
    execution_id = ctx.get("execution_id")
    if not execution_id:
        return

    from db.workflow_store import get_workflow_store

    store = get_workflow_store()
    total_steps = int(ctx.get("total_steps") or 0)
    if status == "completed" and total_steps > 0:
        await store.update_execution(
            str(execution_id),
            completed_steps=total_steps,
        )
    await store.complete_execution(
        str(execution_id),
        status,
        total_cost_usd=total_cost_usd,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        error_message=error_message,
    )


def _track_workflow_step(ctx: dict[str, Any], agent_name: str) -> None:
    _schedule_workflow(_workflow_step_done(ctx, agent_name))


async def _audit_log(
    event_type: str,
    brief: dict[str, Any],
    event_data: dict[str, Any],
) -> None:
    from db.audit_store import get_audit_store

    await get_audit_store().log(
        event_type=event_type,
        actor_type="agent",
        actor_id="pipeline",
        event_data=event_data,
        project_id=str(brief.get("project_id") or "") or None,
    )


async def _emit_agent_start(
    generation_id: str | None,
    *,
    agent: str,
    step: int,
    total: int | None = None,
    session_id: str | None = None,
) -> None:
    total_val = total if total is not None else TRACKED_TOTAL
    await _emit(
        generation_id,
        "agent_start",
        {"agent": agent, "step": step, "total": total_val},
    )
    if session_id:
        from agents.message_bus import message_bus

        message_bus.publish(
            session_id=str(session_id),
            sender_agent="pipeline",
            message_type="agent_started",
            payload={"agent": agent, "step": step, "total": total_val},
            channel_name="pipeline_events",
        )


async def _emit_agent_done(
    generation_id: str | None,
    *,
    agent: str,
    step: int,
    duration_ms: int,
    total: int | None = None,
    usage: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "agent": agent,
        "step": step,
        "duration_ms": duration_ms,
    }
    if total is not None:
        payload["total"] = total
    if isinstance(usage, dict):
        for key in ("input_tokens", "output_tokens", "total_tokens", "model", "provider"):
            if key in usage:
                payload[key] = usage[key]
    await _emit(generation_id, "agent_done", payload)
    if session_id:
        from agents.message_bus import message_bus

        message_bus.publish(
            session_id=str(session_id),
            sender_agent="pipeline",
            message_type="agent_completed",
            payload={"agent": agent, "step": step, "duration_ms": duration_ms},
            channel_name="pipeline_events",
        )


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
    project_id: str | None = None,
    html_quality_score: int = 0,
    session_id: str | None = None,
) -> Any:
    """
    Exécute run_once(prompt) jusqu'à validation SupervisorAI ou timeout 10 min.
    """
    from agents.quality_scorer import QualityScorer

    supervisor = SupervisorAI()
    prompt = (initial_prompt or "").strip()
    attempt = 0
    scorer = QualityScorer()

    async def _loop() -> Any:
        nonlocal prompt, attempt
        last_result: Any = None
        while True:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise MaxRetriesExceeded(
                    f"{agent_name} failed after {MAX_RETRIES} attempts"
                )
            attempt_t0 = time.perf_counter()
            last_result = await run_once(prompt)
            check = await validate(last_result)
            duration_ms = int((time.perf_counter() - attempt_t0) * 1000)

            quality_score = 0
            if agent_name == "BriefAI" and isinstance(last_result, dict):
                quality_score = scorer.score_brief(last_result)
            elif agent_name == "DeployAI" and isinstance(last_result, dict):
                quality_score = scorer.score_deployment(
                    str(last_result.get("url") or ""),
                    html_quality_score,
                )

            _schedule_supervisor_decision(
                decision_type=_decision_type_for_agent(agent_name),
                agent_validated=agent_name,
                valid=bool(check.get("valid")),
                quality_score=quality_score,
                errors=list(check.get("errors") or []),
                warnings=list(check.get("warnings") or []),
                attempt_number=attempt,
                duration_ms=duration_ms,
                generation_id=generation_id,
                project_id=project_id,
            )

            if check.get("valid"):
                if session_id:
                    from agents.message_bus import message_bus

                    message_bus.publish(
                        session_id=str(session_id),
                        sender_agent="supervisor_ai",
                        receiver_agent=_AGENT_RECEIVER_SLUG.get(
                            agent_name, agent_name.lower()
                        ),
                        message_type="validation_passed",
                        payload={"agent": agent_name, "attempt": attempt},
                        channel_name="supervisor_corrections",
                    )
                if success_log:
                    msg = f"[SupervisorAI] ✅ {agent_name} validé — {success_log(last_result)}"
                    print(msg)
                    await _emit_log(generation_id, msg)
                return last_result

            errors = list(check.get("errors") or [])
            _print_supervisor_fail(agent_name, errors)
            reason = "; ".join(str(e) for e in errors) or "validation échouée"
            corrected = str(check.get("corrected_prompt") or "").strip()
            if session_id:
                from agents.message_bus import message_bus

                message_bus.publish(
                    session_id=str(session_id),
                    sender_agent="supervisor_ai",
                    receiver_agent=_AGENT_RECEIVER_SLUG.get(
                        agent_name, agent_name.lower()
                    ),
                    message_type="correction_request",
                    payload={
                        "errors": errors,
                        "corrected_prompt": corrected,
                        "attempt": attempt,
                    },
                    channel_name="supervisor_corrections",
                    priority="high",
                )
            await _emit_log(
                generation_id,
                f"[SupervisorAI] {agent_name} invalide — {reason}",
            )
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
    orchestration_ctx: dict[str, Any] = {
        "session_id": None,
        "agents_completed": [],
        "agents_failed": [],
        "status": "completed",
    }

    try:
        return await _run_pipeline_body_inner(
            req,
            generation_id=generation_id,
            pipeline_t0=pipeline_t0,
            orchestration_ctx=orchestration_ctx,
        )
    except Exception:
        orchestration_ctx["status"] = "failed"
        raise
    finally:
        _orchestration_complete(orchestration_ctx, generation_id)


async def _run_pipeline_body_inner(
    req: PipelineRequest,
    *,
    generation_id: str | None,
    pipeline_t0: float,
    orchestration_ctx: dict[str, Any],
) -> dict[str, Any]:
    supervisor = SupervisorAI()
    brief_ai = BriefAI()
    llm_usage_svc = get_llm_usage_service()
    usage_totals = LLMUsageTotals()
    workflow_ctx = _new_workflow_ctx()
    is_extension = (req.project_type or "").strip().lower() == "extension_navigateur"
    tracked_total = _EXT_TOTAL if is_extension else TRACKED_TOTAL
    html_quality_score = 0

    from agents.planning_engine import PlanningEngine

    pre_brief = {
        "project_type": req.project_type,
        "description": req.prompt,
        "client_name": req.client_name or "",
    }
    execution_plan = PlanningEngine().build_plan(pre_brief)

    if generation_id:
        from db.orchestration_store import get_orchestration_store

        session = await get_orchestration_store().create_session(
            generation_id=generation_id,
            workflow_id=execution_plan["workflow_id"],
            agents_planned=execution_plan["agents"],
            project_id=None,
        )
        if session:
            orchestration_ctx["session_id"] = session.get("id")
    orch_session_id: str | None = orchestration_ctx.get("session_id")
    await _emit_log(
        generation_id,
        (
            f"Plan: {execution_plan['workflow_id']} | "
            f"{len(execution_plan['agents'])} agents | "
            f"~{execution_plan['estimated_cost_usd']:.3f}$ | "
            f"risque: {execution_plan['risk_level']}"
        ),
    )
    async def _audit_pipeline_planned() -> None:
        from db.audit_store import get_audit_store

        await get_audit_store().log(
            "pipeline_planned",
            actor_type="supervisor",
            actor_id="planning_engine",
            event_data={
                "workflow_id": execution_plan["workflow_id"],
                "agents": execution_plan["agents"],
                "estimated_cost": execution_plan["estimated_cost_usd"],
                "risk_level": execution_plan["risk_level"],
                "risk_factors": execution_plan["risk_factors"],
            },
        )

    _schedule_audit(_audit_pipeline_planned())

    async def _run_brief(prompt: str) -> dict[str, Any]:
        return await brief_ai.run(
            prompt=prompt,
            project_type=req.project_type,
            client_name=req.client_name,
        )

    async def _validate_brief(brief: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_brief(brief)

    await _emit_agent_start(
        generation_id,
        agent="BriefAI",
        step=1,
        total=tracked_total,
        session_id=orch_session_id,
    )
    brief_t0 = time.perf_counter()
    brief_raw = await _run_supervised(
        "BriefAI",
        _run_brief,
        _validate_brief,
        initial_prompt=req.prompt,
        success_log=lambda b: f"client: {b.get('client_name', '?')}",
        generation_id=generation_id,
        project_id=None,
        session_id=orch_session_id,
    )
    brief, brief_usage = pop_agent_usage(brief_raw)
    brief_duration_ms = int((time.perf_counter() - brief_t0) * 1000)
    await llm_usage_svc.record_agent(
        "BriefAI",
        brief_usage,
        duration_ms=brief_duration_ms,
        generation_id=generation_id,
        totals=usage_totals,
    )
    await _emit_agent_done(
        generation_id,
        agent="BriefAI",
        step=1,
        duration_ms=brief_duration_ms,
        total=tracked_total,
        usage=brief_usage,
        session_id=orch_session_id,
    )
    _track_orchestration_agent(
        orchestration_ctx, "BriefAI", generation_id=generation_id
    )

    brief["prompt"] = req.prompt
    if req.generation_mode:
        brief["generation_mode"] = req.generation_mode.strip()
    if req.inspiration_brief:
        brief["inspiration_brief"] = req.inspiration_brief.strip()
    if req.firecrawl_result:
        brief["firecrawl_result"] = req.firecrawl_result

    brief["execution_plan"] = PlanningEngine().build_plan(brief)
    pt = (brief.get("project_type") or req.project_type or "").strip().lower()
    project_id = str(brief.get("project_id") or "") or None

    if orch_session_id:
        _schedule_orchestration(
            _orchestration_set_brief_context(str(orch_session_id), dict(brief))
        )

    _schedule_workflow(
        _workflow_init(
            workflow_ctx,
            generation_id=generation_id,
            brief=brief,
            project_type=pt,
        )
    )

    if not is_extension:
        await _emit_agent_start(
            generation_id,
            agent="DesignSystemAI",
            step=2,
            total=tracked_total,
            session_id=orch_session_id,
        )
    ds_t0 = time.perf_counter()
    design_system = DesignSystemAgent().run(brief)
    design_system = supervisor.validate_design_system(design_system, brief)
    brief["design_system"] = design_system
    if not is_extension:
        await _emit_agent_done(
            generation_id,
            agent="DesignSystemAI",
            step=2,
            duration_ms=int((time.perf_counter() - ds_t0) * 1000),
            total=tracked_total,
            session_id=orch_session_id,
        )
        _track_workflow_step(workflow_ctx, "DesignSystemAI")
        _track_orchestration_agent(
            orchestration_ctx, "DesignSystemAI", generation_id=generation_id
        )

    if pt == "extension_navigateur":
        return await _run_extension_pipeline(
            req,
            brief,
            generation_id=generation_id,
            pipeline_t0=pipeline_t0,
            workflow_ctx=workflow_ctx,
            orchestration_ctx=orchestration_ctx,
        )

    if pt not in ("vitrine_next",):
        from agents import database_ai

        base_desc = str(brief.get("description") or req.prompt)

        async def _run_db(prompt: str) -> dict[str, Any]:
            return await database_ai.run(
                project_description=prompt,
                project_type=pt,
                design_system=brief.get("design_system") or {},
            )

        async def _validate_db(schema: dict[str, Any]) -> dict[str, Any]:
            return await supervisor.validate_database(schema, brief)

        await _emit_log(generation_id, "DatabaseAI — schéma base de données")
        db_t0 = time.perf_counter()
        db_raw = await _run_supervised(
            "DatabaseAI",
            _run_db,
            _validate_db,
            initial_prompt=base_desc,
            success_log=lambda s: f"{len((s or {}).get('tables') or [])} table(s)",
            generation_id=generation_id,
            project_id=project_id,
            session_id=orch_session_id,
        )
        db_schema, db_usage = pop_agent_usage(db_raw)
        brief["database_schema"] = db_schema
        if orch_session_id:
            from agents.message_bus import message_bus

            message_bus.publish(
                session_id=str(orch_session_id),
                sender_agent="database_ai",
                message_type="schema_ready",
                payload={
                    "tables": len((db_schema or {}).get("tables") or []),
                    "project_type": pt,
                },
                channel_name="schema_propagation",
            )
        await llm_usage_svc.record_agent(
            "DatabaseAI",
            db_usage,
            duration_ms=int((time.perf_counter() - db_t0) * 1000),
            generation_id=generation_id,
            totals=usage_totals,
        )
        _track_workflow_step(workflow_ctx, "DatabaseAI")
        _track_orchestration_agent(
            orchestration_ctx, "DatabaseAI", generation_id=generation_id
        )

    if pt in ("application_web", "real_app", "crm"):
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
        auth_t0 = time.perf_counter()
        auth_raw = await _run_supervised(
            "AuthAI",
            _run_auth,
            _validate_auth,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda s: f"auth_type={s.get('auth_type', '?')}",
            generation_id=generation_id,
            project_id=project_id,
            session_id=orch_session_id,
        )
        auth_schema, auth_usage = pop_agent_usage(auth_raw)
        brief["auth_schema"] = auth_schema
        await llm_usage_svc.record_agent(
            "AuthAI",
            auth_usage,
            duration_ms=int((time.perf_counter() - auth_t0) * 1000),
            generation_id=generation_id,
            totals=usage_totals,
        )
        _track_workflow_step(workflow_ctx, "AuthAI")
        _track_orchestration_agent(
            orchestration_ctx, "AuthAI", generation_id=generation_id
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
        pay_t0 = time.perf_counter()
        pay_raw = await _run_supervised(
            "PaymentAI",
            _run_payment,
            _validate_payment,
            initial_prompt=str(brief.get("description") or req.prompt),
            success_log=lambda p: f"type={p.get('payment_type', '?')}",
            generation_id=generation_id,
            project_id=project_id,
            session_id=orch_session_id,
        )
        payment_cfg, pay_usage = pop_agent_usage(pay_raw)
        brief["payment_config"] = payment_cfg
        await llm_usage_svc.record_agent(
            "PaymentAI",
            pay_usage,
            duration_ms=int((time.perf_counter() - pay_t0) * 1000),
            generation_id=generation_id,
            totals=usage_totals,
        )
        _track_workflow_step(workflow_ctx, "PaymentAI")
        _track_orchestration_agent(
            orchestration_ctx, "PaymentAI", generation_id=generation_id
        )

    _apply_stripe_publishable_key(brief, req.stripe_publishable_key)

    from agents.parallel_executor import parallel_executor

    try:
        from knowledge.knowledge_service import get_knowledge_service
        from memory.memory_service import get_memory_service

        knowledge_service = get_knowledge_service()
        memory_service = get_memory_service()
        query = str(brief.get("description") or req.prompt)
        proj_id = brief.get("project_id")

        contexts = await parallel_executor.run_parallel(
            {
                "knowledge": knowledge_service.get_context_for_prompt(
                    query=query,
                    project_id=proj_id,
                ),
                "memory": memory_service.get_context_for_prompt(
                    query=query,
                    project_id=proj_id,
                ),
            }
        )
        brief["knowledge_context"] = contexts.get("knowledge") or ""
        brief["memory_context"] = contexts.get("memory") or ""

        if orch_session_id:
            from agents.message_bus import message_bus

            message_bus.publish(
                session_id=str(orch_session_id),
                sender_agent="context_enrichment",
                receiver_agent="generator_ai",
                message_type="context_ready",
                payload={
                    "has_knowledge": bool(contexts.get("knowledge")),
                    "has_memory": bool(contexts.get("memory")),
                },
                channel_name="context_enrichment",
            )

        if generation_id:
            _schedule_orchestration(
                _orchestration_update_session(
                    generation_id,
                    orchestration_ctx,
                    parallel_groups=[["knowledge", "memory"]],
                )
            )
            await _emit(
                generation_id,
                "log",
                {"message": "Knowledge + Memory récupérés en parallèle"},
            )
    except Exception as exc:
        logger.warning("[Pipeline] Knowledge/Memory parallèle indisponible — %s", exc)

    generator = GeneratorAI()

    await _emit_agent_start(
        generation_id,
        agent="GeneratorAI",
        step=3,
        total=tracked_total,
        session_id=orch_session_id,
    )
    gen_t0 = time.perf_counter()
    correction = ""
    result: dict[str, Any] = {}

    async def _run_generator_once() -> dict[str, Any]:
        fixes = correction.strip() or None
        return await generator.run(brief, corrections=fixes)

    result = await _run_generator_once()
    result, gen_usage = pop_agent_usage(result)
    gen_duration_ms = int((time.perf_counter() - gen_t0) * 1000)
    await llm_usage_svc.record_agent(
        "GeneratorAI",
        gen_usage,
        duration_ms=gen_duration_ms,
        generation_id=generation_id,
        totals=usage_totals,
    )
    await _emit_agent_done(
        generation_id,
        agent="GeneratorAI",
        step=3,
        duration_ms=gen_duration_ms,
        total=tracked_total,
        usage=gen_usage,
        session_id=orch_session_id,
    )
    _track_workflow_step(workflow_ctx, "GeneratorAI")
    _track_orchestration_agent(
        orchestration_ctx, "GeneratorAI", generation_id=generation_id
    )

    await _emit_agent_start(
        generation_id,
        agent="SupervisorAI",
        step=4,
        total=tracked_total,
        session_id=orch_session_id,
    )
    sup_t0 = time.perf_counter()

    async def _supervisor_html_loop() -> None:
        nonlocal result, correction, html_quality_score
        from agents.quality_scorer import QualityScorer

        scorer = QualityScorer()
        attempt = 0
        while True:
            attempt += 1
            if attempt > MAX_HTML_RETRIES:
                raise MaxRetriesExceeded(
                    f"SupervisorAI failed after {MAX_HTML_RETRIES} attempts"
                )
            html_t0 = time.perf_counter()
            html = str((result or {}).get("html") or "")
            check = await supervisor.validate_html(html, brief)
            duration_ms = int((time.perf_counter() - html_t0) * 1000)
            html_score_attempt = scorer.score_html(html, brief)

            _schedule_supervisor_decision(
                decision_type="html",
                agent_validated="SupervisorAI",
                valid=bool(check.get("valid")),
                quality_score=html_score_attempt,
                errors=list(check.get("errors") or []),
                warnings=list(check.get("warnings") or []),
                attempt_number=attempt,
                duration_ms=duration_ms,
                generation_id=generation_id,
                project_id=project_id,
            )

            if check.get("valid"):
                html_quality_score = html_score_attempt
                _schedule_quality_review(
                    review_type="html_quality",
                    score=html_quality_score,
                    passed=html_quality_score >= 60,
                    details={"html_length": len(html)},
                    generation_id=generation_id,
                    project_id=project_id,
                )
                if orch_session_id:
                    from agents.message_bus import message_bus

                    message_bus.publish(
                        session_id=str(orch_session_id),
                        sender_agent="supervisor_ai",
                        receiver_agent="generator_ai",
                        message_type="validation_passed",
                        payload={"html_length": len(html), "attempt": attempt},
                        channel_name="supervisor_corrections",
                    )
                msg = f"[SupervisorAI] ✅ HTML validé — {len(html)} car."
                print(msg)
                await _emit_log(generation_id, msg)
                return

            errors = list(check.get("errors") or [])
            _print_supervisor_fail("SupervisorAI", errors)
            reason = "; ".join(str(e) for e in errors) or "HTML invalide"
            corrected = str(check.get("corrected_prompt") or "").strip()
            if orch_session_id and not check.get("valid"):
                from agents.message_bus import message_bus

                message_bus.publish(
                    session_id=str(orch_session_id),
                    sender_agent="supervisor_ai",
                    receiver_agent="generator_ai",
                    message_type="correction_request",
                    payload={
                        "errors": errors,
                        "corrected_prompt": corrected,
                        "attempt": attempt,
                    },
                    channel_name="supervisor_corrections",
                    priority="high",
                )
            await _emit_agent_retry(
                generation_id,
                agent="SupervisorAI",
                attempt=attempt,
                reason=reason,
            )
            correction = corrected
            _print_supervisor_retry("SupervisorAI", attempt + 1)
            gen_retry_t0 = time.perf_counter()
            retry_raw = await generator.run(brief, corrections=correction or None)
            result, retry_usage = pop_agent_usage(retry_raw)
            await llm_usage_svc.record_agent(
                "GeneratorAI",
                retry_usage,
                duration_ms=int((time.perf_counter() - gen_retry_t0) * 1000),
                generation_id=generation_id,
                totals=usage_totals,
            )
            await _emit_log(
                generation_id,
                f"GeneratorAI — regénération après rejet ({int((time.perf_counter() - gen_retry_t0) * 1000)} ms)",
            )

    await asyncio.wait_for(_supervisor_html_loop(), timeout=AGENT_TIMEOUT_SECONDS)
    await _emit_agent_done(
        generation_id,
        agent="SupervisorAI",
        step=4,
        duration_ms=int((time.perf_counter() - sup_t0) * 1000),
        total=tracked_total,
        session_id=orch_session_id,
    )
    _track_workflow_step(workflow_ctx, "SupervisorAI")
    _track_orchestration_agent(
        orchestration_ctx, "SupervisorAI", generation_id=generation_id
    )

    html_for_context = str((result or {}).get("html") or "")
    if orch_session_id and html_for_context:
        _schedule_orchestration(
            _orchestration_set_html_context(
                str(orch_session_id),
                len(html_for_context),
                html_quality_score,
            )
        )

    if not result.get("success") or not result.get("html"):
        error_msg = "GeneratorAI n'a pas produit de HTML valide."
        orchestration_ctx["status"] = "failed"
        await _emit(generation_id, "error", {"message": error_msg})
        _schedule_workflow(
            _workflow_complete(
                workflow_ctx,
                status="failed",
                duration_ms=int((time.perf_counter() - pipeline_t0) * 1000),
                error_message=error_msg,
            )
        )
        _schedule_audit(
            _audit_log(
                "generation_failed",
                brief,
                {
                    "error": error_msg,
                    "project_type": str(brief.get("project_type") or req.project_type or ""),
                },
            )
        )
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
            design_system=brief.get("design_system"),
            brief=brief,
        )

    async def _validate_deploy(deployed: dict[str, Any]) -> dict[str, Any]:
        return await supervisor.validate_deployment(
            str(deployed.get("url") or ""),
            client_name,
        )

    await _emit_agent_start(
        generation_id,
        agent="DeployAI",
        step=5,
        total=tracked_total,
        session_id=orch_session_id,
    )
    deploy_t0 = time.perf_counter()
    deployed = await _run_supervised(
        "DeployAI",
        _run_deploy,
        _validate_deploy,
        initial_prompt="",
        success_log=lambda d: f"URL: {d.get('url', '')}",
        generation_id=generation_id,
        project_id=project_id,
        html_quality_score=html_quality_score,
        session_id=orch_session_id,
    )
    await _emit_agent_done(
        generation_id,
        agent="DeployAI",
        step=5,
        duration_ms=int((time.perf_counter() - deploy_t0) * 1000),
        total=tracked_total,
        session_id=orch_session_id,
    )
    _track_workflow_step(workflow_ctx, "DeployAI")
    _track_orchestration_agent(
        orchestration_ctx, "DeployAI", generation_id=generation_id
    )

    deploy_url = str(deployed.get("url") or "")
    persisted_project_id: str | None = None
    if deployed.get("success") and deploy_url:
        store = get_supabase_store()
        if store.is_configured():
            try:
                metrics = usage_totals.as_dict()
                persistence = await store.save_pipeline_v2_deploy(
                    prompt=req.prompt,
                    project_type=str(
                        brief.get("project_type") or req.project_type or "vitrine_next"
                    ),
                    client_name=client_name,
                    demo_url=deploy_url,
                    html=str(deployed.get("html") or result.get("html") or ""),
                    duration_ms=int((time.perf_counter() - pipeline_t0) * 1000),
                    estimated_cost_usd=float(metrics.get("estimated_cost_usd") or 0),
                    input_tokens=int(metrics.get("input_tokens") or 0),
                    output_tokens=int(metrics.get("output_tokens") or 0),
                    total_tokens=int(metrics.get("total_tokens") or 0),
                    generation_id=generation_id,
                )
                if persistence:
                    persisted_project_id = persistence.project_id
            except SupabaseStoreError as exc:
                logger.warning("[pipeline] persistance Supabase ignorée: %s", exc)

    total_duration_ms = int((time.perf_counter() - pipeline_t0) * 1000)
    usage_summary = usage_totals.as_dict()
    await llm_usage_svc.finalize_generation(
        generation_id=generation_id,
        project_id=persisted_project_id,
        success=bool(deployed.get("success")),
    )
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
        "input_tokens": usage_summary.get("input_tokens", 0),
        "output_tokens": usage_summary.get("output_tokens", 0),
        "total_tokens": usage_summary.get("total_tokens", 0),
        "estimated_cost_usd": usage_summary.get("estimated_cost_usd", 0),
        "llm_usage": usage_summary.get("agents", []),
        "quality_score": html_quality_score,
    }

    if final_result["success"]:
        await _emit(
            generation_id,
            "done",
            {
                "url": str(final_result.get("url") or ""),
                "html": str(final_result.get("html") or ""),
                "duration_ms": total_duration_ms,
                "input_tokens": final_result.get("input_tokens", 0),
                "output_tokens": final_result.get("output_tokens", 0),
                "total_tokens": final_result.get("total_tokens", 0),
                "estimated_cost_usd": final_result.get("estimated_cost_usd", 0),
                "quality_score": html_quality_score,
                "unlock_url": final_result.get("unlock_url"),
                "demo_token": final_result.get("demo_token"),
                "demo_password": final_result.get("demo_password"),
            },
        )

        async def _send_deploy_email() -> None:
            try:
                from agents.email_ai import send_deployment_notification

                await send_deployment_notification(
                    brief=brief,
                    demo_url=str(final_result.get("url") or ""),
                    duration_ms=total_duration_ms,
                )
            except Exception as exc:
                logger.warning(
                    "[EmailAI] notification déploiement ignorée: %s", exc
                )

        asyncio.create_task(_send_deploy_email())

        async def _remember_generation() -> None:
            try:
                from memory.memory_service import get_memory_service

                await get_memory_service().remember_generation(
                    brief=brief,
                    result={
                        "url": str(final_result.get("url") or ""),
                        "duration_ms": total_duration_ms,
                    },
                )
            except Exception as exc:
                logger.warning("[MemoryEngine] remember_generation ignoré — %s", exc)

        asyncio.create_task(_remember_generation())

        _schedule_audit(
            _audit_log(
                "project_generated",
                brief,
                {
                    "project_type": str(brief.get("project_type") or req.project_type or ""),
                    "client_name": str(brief.get("client_name") or req.client_name or ""),
                    "url": str(final_result.get("url") or ""),
                    "duration_ms": total_duration_ms,
                    "cost_usd": float(final_result.get("estimated_cost_usd") or 0),
                },
            )
        )
        _schedule_workflow(
            _workflow_complete(
                workflow_ctx,
                status="completed",
                total_cost_usd=float(final_result.get("estimated_cost_usd") or 0),
                total_tokens=int(final_result.get("total_tokens") or 0),
                duration_ms=total_duration_ms,
            )
        )
    else:
        err = str(final_result.get("error") or "Déploiement échoué")
        orchestration_ctx["status"] = "failed"
        await _emit(generation_id, "error", {"message": err})
        _schedule_audit(
            _audit_log(
                "generation_failed",
                brief,
                {
                    "error": err,
                    "project_type": str(brief.get("project_type") or req.project_type or ""),
                },
            )
        )
        _schedule_workflow(
            _workflow_complete(
                workflow_ctx,
                status="failed",
                total_cost_usd=float(final_result.get("estimated_cost_usd") or 0),
                total_tokens=int(final_result.get("total_tokens") or 0),
                duration_ms=total_duration_ms,
                error_message=err,
            )
        )

    return final_result


async def _run_extension_pipeline(
    req: PipelineRequest,
    brief: dict[str, Any],
    *,
    generation_id: str | None,
    pipeline_t0: float,
    workflow_ctx: dict[str, Any] | None = None,
    orchestration_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """BriefAI → ExtensionBuilder → DeployAI (pas Generator/DB/Auth/Payment)."""
    from tools.extension_pipeline import build_extension_files, build_extension_zip

    wf_ctx = workflow_ctx or _new_workflow_ctx()
    orch_ctx = orchestration_ctx if orchestration_ctx is not None else {
        "session_id": None,
        "agents_completed": [],
        "agents_failed": [],
        "status": "completed",
    }
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
    _track_workflow_step(wf_ctx, "ExtensionBuilder")
    _track_orchestration_agent(
        orch_ctx, "ExtensionBuilder", generation_id=generation_id
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
    ext_project_id = str(brief.get("project_id") or "") or None
    ext_session_id = orch_ctx.get("session_id")
    deployed = await _run_supervised(
        "DeployAI",
        _run_deploy,
        _validate_deploy,
        initial_prompt="",
        success_log=lambda d: f"URL: {d.get('url', '')}",
        generation_id=generation_id,
        project_id=ext_project_id,
        html_quality_score=0,
        session_id=ext_session_id,
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
    _track_workflow_step(wf_ctx, "DeployAI")
    _track_orchestration_agent(
        orch_ctx, "DeployAI", generation_id=generation_id
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

        async def _send_extension_deploy_email() -> None:
            try:
                from agents.email_ai import send_deployment_notification

                await send_deployment_notification(
                    brief=brief,
                    demo_url=str(final_result.get("url") or ""),
                    duration_ms=total_duration_ms,
                )
            except Exception as exc:
                logger.warning(
                    "[EmailAI] notification déploiement extension ignorée: %s", exc
                )

        asyncio.create_task(_send_extension_deploy_email())

        async def _remember_extension_generation() -> None:
            try:
                from memory.memory_service import get_memory_service

                await get_memory_service().remember_generation(
                    brief=brief,
                    result={
                        "url": str(final_result.get("url") or ""),
                        "duration_ms": total_duration_ms,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "[MemoryEngine] remember_generation extension ignoré — %s", exc
                )

        asyncio.create_task(_remember_extension_generation())

        _schedule_audit(
            _audit_log(
                "project_generated",
                brief,
                {
                    "project_type": "extension_navigateur",
                    "client_name": client_name,
                    "url": str(final_result.get("url") or ""),
                    "duration_ms": total_duration_ms,
                    "cost_usd": 0,
                },
            )
        )
        _schedule_workflow(
            _workflow_complete(
                wf_ctx,
                status="completed",
                duration_ms=total_duration_ms,
            )
        )
    else:
        err = str(final_result.get("error") or "Déploiement extension échoué")
        orch_ctx["status"] = "failed"
        await _emit(generation_id, "error", {"message": err})
        _schedule_audit(
            _audit_log(
                "generation_failed",
                brief,
                {
                    "error": err,
                    "project_type": "extension_navigateur",
                },
            )
        )
        _schedule_workflow(
            _workflow_complete(
                wf_ctx,
                status="failed",
                duration_ms=total_duration_ms,
                error_message=err,
            )
        )

    return final_result
