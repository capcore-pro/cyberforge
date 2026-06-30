"""
OpenHands Router — CyberForge
Endpoints pour le mode Debug client (bouton par projet).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.openhands_pipeline import run_debug_pipeline
from db.audit_store import get_audit_store
from db.supabase_store import SupabaseStoreError, get_supabase_store
from tools.export_cloudflare import CloudflareExportError, deploy_html_demo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["openhands"])


def _not_configured_detail(store: Any) -> dict[str, Any]:
    return {
        "message": (
            "Supabase non configuré. Ajoutez SUPABASE_URL et "
            "SUPABASE_SECRET_KEY dans backend/.env."
        ),
        "diagnostics": store.connection_diagnostics(),
    }


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    upstream = detail.pop("status_code", None)
    if upstream is not None:
        detail["upstream_status_code"] = upstream
    status = 502
    if upstream == 401:
        status = 401
    if "introuvable" in str(exc).lower():
        status = 404
    return HTTPException(status_code=status, detail=detail)


class DebugRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    project_type: str = Field(
        ...,
        min_length=1,
        description="website, mobile, desktop, erp, extension, site_web, ecommerce…",
    )
    project_name: str | None = ""
    redeploy_after: bool = True


class DebugResponse(BaseModel):
    success: bool
    project_id: str
    iterations: int
    issues_found: list[str]
    corrections_applied: list[str]
    quality_score: float
    redeployed: bool
    deploy_url: str | None = None
    report: dict[str, Any]


@router.post("/openhands/debug", response_model=DebugResponse)
async def debug_project(request: DebugRequest) -> DebugResponse:
    """
    Mode Debug — analyse, corrige et redéploie un projet existant.
    Déclenché depuis le bouton « Analyser & Corriger » dans CyberForge.
    """
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    try:
        editor_ctx = await store.get_editor_html(request.project_id.strip())
        if editor_ctx is None or not str(editor_ctx.get("html") or "").strip():
            raise HTTPException(
                status_code=404,
                detail="Code projet introuvable dans Supabase.",
            )

        code = str(editor_ctx["html"])
        project_name = (request.project_name or editor_ctx.get("project_title") or request.project_id).strip()

        logger.info(
            "OpenHands Debug — projet %s (%s)",
            request.project_id,
            request.project_type,
        )

        result = await run_debug_pipeline(
            code=code,
            project_type=request.project_type,
            project_name=project_name,
        )

        corrected_code = str(result.get("corrected_code") or code)
        report = dict(result.get("report") or {})

        await store.save_editor_html(
            request.project_id.strip(),
            str(editor_ctx["generation_id"]),
            corrected_code,
            html_before=code,
            edit_type="openhands_correction",
        )

        deploy_url: str | None = None
        redeployed = False
        if request.redeploy_after and corrected_code.strip():
            try:
                deploy_url = await _redeploy_project_html(
                    store,
                    project_id=request.project_id.strip(),
                    generation_id=str(editor_ctx["generation_id"]),
                    html=corrected_code,
                    project_type=str(
                        editor_ctx.get("project_type") or request.project_type
                    ),
                    title=str(editor_ctx.get("project_title") or "CyberForge"),
                )
                redeployed = bool(deploy_url)
                if deploy_url:
                    logger.info("OpenHands Debug — redéployé sur %s", deploy_url)
            except CloudflareExportError as exc:
                logger.error("OpenHands Debug — redéploiement échoué: %s", exc)

        await store.save_openhands_correction(
            request.project_id.strip(),
            iterations=int(result.get("iterations") or 0),
            issues_found=list(report.get("issues") or []),
            corrections_applied=list(report.get("corrections") or []),
            quality_score=float(report.get("quality_score_final") or 0),
            report=report,
            redeployed=redeployed,
            deploy_url=deploy_url,
        )

        await get_audit_store().log(
            "openhands_debug",
            project_id=request.project_id.strip(),
            event_data={
                "iterations": result.get("iterations", 0),
                "issues_count": len(report.get("issues") or []),
                "quality_score": report.get("quality_score_final", 0),
                "redeployed": redeployed,
                "deploy_url": deploy_url,
            },
        )

        return DebugResponse(
            success=True,
            project_id=request.project_id.strip(),
            iterations=int(result.get("iterations") or 0),
            issues_found=[str(x) for x in (report.get("issues") or [])],
            corrections_applied=[str(x) for x in (report.get("corrections") or [])],
            quality_score=float(report.get("quality_score_final") or 0),
            redeployed=redeployed,
            deploy_url=deploy_url,
            report=report,
        )
    except HTTPException:
        raise
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /api/openhands/debug") from exc
    except Exception as exc:
        logger.error("OpenHands Debug error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/openhands/report/{project_id}")
async def get_debug_report(project_id: str) -> dict[str, Any]:
    """Récupère le dernier rapport OpenHands pour un projet."""
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail=_not_configured_detail(store))

    row = await store.get_latest_openhands_correction(project_id.strip())
    if row is None:
        return {"project_id": project_id, "report": None}
    return {"project_id": project_id, "report": row}


async def _redeploy_project_html(
    store: Any,
    *,
    project_id: str,
    generation_id: str,
    html: str,
    project_type: str,
    title: str,
) -> str:
    production_url, _token, _password, unlock_url = await deploy_html_demo(
        html=html.strip(),
        title=title,
        project_type=project_type,
    )
    live_url = (unlock_url or production_url).strip().rstrip("/")
    await store.update_project_demo_url(project_id, live_url)
    await get_audit_store().log(
        "openhands_debug_deployed",
        project_id=project_id,
        event_data={"generation_id": generation_id, "url": live_url},
    )

    try:
        from agents.portal_onboarding_agent import notify_portal_client_site_updated

        notify_portal_client_site_updated(project_id, live_url)
    except Exception as e:
        logger.warning("Notification email échouée (non bloquant): %s", e)

    return live_url
