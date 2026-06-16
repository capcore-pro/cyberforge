"""
Routes API — Mobile Builder (MobileAI + EAS Build).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from agents.mobile_ai import ALL_FEATURES, ALL_SECTORS, analyze_brief, generate_mobile_app
from db.mobile_app_store import get_mobile_app_store
from db.supabase_store import SupabaseStoreError
from tools.eas_builder import (
    EasBuilderError,
    check_build_status,
    download_apk,
    get_build_root,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile_builder"])


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


MobileMode = Literal["client", "product"]
MobileSector = Literal["restaurant", "artisan", "commerce", "service", "vitrine"]


class MobileAppCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    mode: MobileMode = "client"
    sector: MobileSector = "vitrine"
    primary_color: str = Field(default="#06b6d4", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#8b5cf6", pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = None
    app_slug: str = Field(..., min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    bundle_id: str = Field(default="", max_length=120)
    features: list[str] = Field(default_factory=list)


class MobileAppUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    mode: MobileMode | None = None
    sector: MobileSector | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = None
    app_slug: str | None = Field(default=None, min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    bundle_id: str | None = Field(default=None, max_length=120)
    features: list[str] | None = None


def _validate_features(features: list[str]) -> list[str]:
    return [f for f in features if f in ALL_FEATURES]


def _row_to_app(row: dict[str, Any]) -> dict[str, Any]:
    features = row.get("features")
    screens = row.get("screens")
    if not isinstance(features, list):
        features = []
    if not isinstance(screens, list):
        screens = []
    return {
        "id": str(row.get("id") or ""),
        "name": str(row.get("name") or ""),
        "description": row.get("description"),
        "mode": row.get("mode"),
        "sector": row.get("sector"),
        "primary_color": row.get("primary_color"),
        "secondary_color": row.get("secondary_color"),
        "logo_url": row.get("logo_url"),
        "app_slug": row.get("app_slug"),
        "bundle_id": row.get("bundle_id"),
        "features": features,
        "screens": screens,
        "status": row.get("status") or "draft",
        "eas_build_id": row.get("eas_build_id"),
        "apk_url": row.get("apk_url"),
        "build_logs": row.get("build_logs"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


@router.post("/mobile/apps")
async def create_mobile_app(body: MobileAppCreate) -> dict[str, Any]:
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    existing = await store.get_app_by_slug(body.app_slug)
    if existing:
        raise HTTPException(status_code=409, detail="Ce slug est déjà utilisé.")
    features = _validate_features(body.features)
    bundle_id = body.bundle_id.strip() or f"com.capcore.{body.app_slug.replace('-', '')}"
    try:
        row = await store.create_app(
            {
                "name": body.name.strip(),
                "description": body.description.strip(),
                "mode": body.mode,
                "sector": body.sector,
                "primary_color": body.primary_color,
                "secondary_color": body.secondary_color,
                "logo_url": body.logo_url,
                "app_slug": body.app_slug.strip(),
                "bundle_id": bundle_id,
                "features": features,
                "screens": [],
                "status": "draft",
            }
        )
        return _row_to_app(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/mobile/apps")
async def list_mobile_apps() -> dict[str, Any]:
    store = get_mobile_app_store()
    if not store.is_configured():
        return {"items": [], "count": 0}
    try:
        rows = await store.list_apps()
        items = [_row_to_app(r) for r in rows]
        return {"items": items, "count": len(items)}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/mobile/apps/{app_id}")
async def get_mobile_app(app_id: str) -> dict[str, Any]:
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        row = await store.get_app(app_id)
        if not row:
            raise HTTPException(status_code=404, detail="App introuvable.")
        return _row_to_app(row)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/mobile/apps/{app_id}")
async def update_mobile_app(app_id: str, body: MobileAppUpdate) -> dict[str, Any]:
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    patch = body.model_dump(exclude_unset=True)
    if "features" in patch and patch["features"] is not None:
        patch["features"] = _validate_features(patch["features"])
    if "app_slug" in patch and patch["app_slug"]:
        existing = await store.get_app_by_slug(patch["app_slug"])
        if existing and str(existing.get("id")) != app_id:
            raise HTTPException(status_code=409, detail="Ce slug est déjà utilisé.")
    try:
        updated = await store.update_app(app_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail="App introuvable.")
        return _row_to_app(updated)
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/mobile/apps/{app_id}")
async def delete_mobile_app(app_id: str) -> dict[str, Any]:
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        ok = await store.delete_app(app_id)
        if not ok:
            raise HTTPException(status_code=404, detail="App introuvable.")
        return {"deleted": True, "id": app_id}
    except SupabaseStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/mobile/apps/{app_id}/generate")
async def generate_mobile_app_stream(app_id: str, request: Request) -> StreamingResponse:
    """Lance MobileAI et streame la progression en SSE."""

    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_app(app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App introuvable.")

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _sse_event("agent_start", {"message": "MobileAI analyse le brief..."})
            await asyncio.sleep(0.3)
            if await request.is_disconnected():
                return

            brief = await analyze_brief(row)
            yield _sse_event("agent_done", {"message": "Structure générée", "brief": brief})
            await asyncio.sleep(0.2)

            yield _sse_event("agent_start", {"message": "Génération des écrans..."})
            result = await generate_mobile_app(row)
            file_list = sorted(result.files.keys())
            yield _sse_event(
                "agent_done",
                {"message": "Écrans créés", "files": file_list, "count": len(file_list)},
            )
            await asyncio.sleep(0.2)

            yield _sse_event("agent_start", {"message": "Configuration EAS..."})
            await store.update_app(
                app_id,
                {
                    "screens": result.screens,
                    "features": result.features,
                    "status": "generated",
                },
            )
            yield _sse_event("agent_done", {"message": "Prêt à compiler"})
            yield _sse_event(
                "done",
                {
                    "app_id": app_id,
                    "screens_count": len(result.screens),
                    "features_count": len(result.features),
                    "files": file_list,
                },
            )
        except Exception as exc:
            logger.exception("MobileAI generate failed for %s", app_id)
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mobile/apps/{app_id}/build")
async def build_mobile_apk(app_id: str) -> dict[str, Any]:
    """Lance un build EAS Android en arrière-plan."""
    from tools.eas_builder import trigger_eas_build

    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_app(app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App introuvable.")
    if row.get("status") not in ("generated", "ready", "building", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Générez d'abord l'app avec MobileAI avant de lancer le build.",
        )

    build_number = await store.next_build_number(app_id)
    build_row = await store.create_build(
        {"app_id": app_id, "build_number": build_number, "status": "pending"}
    )
    build_id = str(build_row.get("id") or "")

    await store.update_app(app_id, {"status": "building", "build_logs": "Build EAS démarré..."})

    async def _run_build() -> None:
        start = time.perf_counter()
        try:
            eas_build_id = await trigger_eas_build(app_id)
            duration_ms = int((time.perf_counter() - start) * 1000)
            await store.update_build(
                build_id,
                {"eas_build_id": eas_build_id, "status": "in_progress"},
            )
            await store.update_app(
                app_id,
                {
                    "eas_build_id": eas_build_id,
                    "status": "building",
                    "build_logs": f"Build EAS lancé: {eas_build_id}",
                },
            )
            # Polling initial rapide
            for _ in range(60):
                await asyncio.sleep(30)
                status_info = await check_build_status(eas_build_id)
                st = status_info.get("status", "")
                apk_url = status_info.get("apk_url")
                if st in ("finished", "completed", "complete"):
                    local_apk: str | None = None
                    if apk_url:
                        try:
                            path = await download_apk(apk_url, app_id)
                            local_apk = str(path)
                        except Exception as dl_exc:
                            logger.warning("APK download failed: %s", dl_exc)
                    await store.update_build(
                        build_id,
                        {
                            "status": "finished",
                            "apk_url": apk_url,
                            "build_duration_ms": int((time.perf_counter() - start) * 1000),
                        },
                    )
                    await store.update_app(
                        app_id,
                        {
                            "status": "ready",
                            "apk_url": apk_url,
                            "build_logs": f"Build terminé. APK: {apk_url or local_apk}",
                        },
                    )
                    return
                if st in ("errored", "failed", "canceled", "cancelled"):
                    await store.update_build(build_id, {"status": "failed"})
                    await store.update_app(
                        app_id,
                        {
                            "status": "failed",
                            "build_logs": str(status_info.get("error") or "Build EAS échoué"),
                        },
                    )
                    return
        except EasBuilderError as exc:
            await store.update_build(build_id, {"status": "failed"})
            await store.update_app(
                app_id,
                {"status": "failed", "build_logs": str(exc)},
            )
        except Exception as exc:
            logger.exception("EAS build failed for %s", app_id)
            await store.update_build(build_id, {"status": "failed"})
            await store.update_app(
                app_id,
                {"status": "failed", "build_logs": str(exc)},
            )

    asyncio.create_task(_run_build())
    return {
        "app_id": app_id,
        "build_id": build_id,
        "status": "building",
        "message": "Build EAS lancé en arrière-plan.",
    }


@router.get("/mobile/apps/{app_id}/status")
async def get_mobile_build_status(app_id: str) -> dict[str, Any]:
    """Statut du build en cours ou dernier build."""
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_app(app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App introuvable.")

    eas_build_id = row.get("eas_build_id")
    live_status: dict[str, Any] | None = None
    if eas_build_id and row.get("status") == "building":
        try:
            live_status = await check_build_status(str(eas_build_id))
            st = live_status.get("status", "")
            apk_url = live_status.get("apk_url")
            if st in ("finished", "completed", "complete") and apk_url:
                await store.update_app(
                    app_id,
                    {"status": "ready", "apk_url": apk_url, "build_logs": "Build terminé."},
                )
                row = await store.get_app(app_id) or row
            elif st in ("errored", "failed", "canceled", "cancelled"):
                await store.update_app(
                    app_id,
                    {
                        "status": "failed",
                        "build_logs": str(live_status.get("error") or "Build échoué"),
                    },
                )
                row = await store.get_app(app_id) or row
        except EasBuilderError:
            pass

    builds = await store.list_builds(app_id)
    return {
        "app": _row_to_app(row),
        "live": live_status,
        "builds": builds,
        "sectors": ALL_SECTORS,
        "features": ALL_FEATURES,
    }


@router.get("/mobile/apps/{app_id}/download", response_model=None)
async def download_mobile_apk(app_id: str) -> FileResponse | dict[str, Any]:
    """Télécharge l'APK local ou retourne l'URL distante."""
    store = get_mobile_app_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    row = await store.get_app(app_id)
    if not row:
        raise HTTPException(status_code=404, detail="App introuvable.")

    local_path = get_build_root(app_id) / "app-release.apk"
    if local_path.exists():
        return FileResponse(
            path=str(local_path),
            media_type="application/vnd.android.package-archive",
            filename=f"{row.get('app_slug', 'app')}.apk",
        )

    apk_url = row.get("apk_url")
    if apk_url:
        return {"download_url": apk_url, "app_id": app_id}

    raise HTTPException(status_code=404, detail="APK non disponible. Lancez un build d'abord.")
