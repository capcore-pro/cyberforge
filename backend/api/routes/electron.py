"""
Electron Router — CyberForge
Endpoints pour la compilation .exe clients et la gestion des licences.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from agents.electron_ai import run as electron_ai_run
from agents.electron_compiler import electron_compiler
from agents.license_manager import license_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/electron", tags=["electron"])


class BuildRequest(BaseModel):
    project_id: str
    client_name: str
    client_email: str
    app_name: str
    app_description: str
    project_type: str = "desktop"
    model: Literal["one_shot", "subscription"] = "one_shot"
    price_one_shot: float = 0
    price_monthly: float = 0
    version: str = "1.0.0"
    assembled_html: str = ""
    database_schema: dict[str, Any] = Field(default_factory=dict)


class LicenseCheckRequest(BaseModel):
    license_key: str


class LicenseDeactivateRequest(BaseModel):
    license_key: str


def _supabase():
    return license_manager.supabase


@router.post("/build")
async def build_desktop_app(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Lance la génération + compilation .exe pour un client.
    1. ElectronAI génère les fichiers
    2. ElectronCompiler pousse sur GitHub + déclenche Actions
    3. Crée la licence dans Supabase
    4. Retourne le build_id pour polling
    """
    try:
        logger.info("ElectronBuild — génération code : %s", request.app_name)
        electron_files = await electron_ai_run(
            project_description=request.app_description,
            assembled_html=request.assembled_html,
            database_schema=request.database_schema,
        )

        files = dict(electron_files.get("files") or {})
        if not files:
            raise HTTPException(
                status_code=500,
                detail="ElectronAI n'a pas généré de fichiers",
            )

        build_data = {
            "project_id": request.project_id.strip(),
            "client_name": request.client_name.strip(),
            "client_email": request.client_email.strip(),
            "app_name": request.app_name.strip(),
            "app_description": request.app_description.strip(),
            "project_type": request.project_type,
            "model": request.model,
            "price_one_shot": request.price_one_shot,
            "price_monthly": request.price_monthly,
            "build_status": "pending",
            "version": request.version,
        }
        build_result = _supabase().table("electron_builds").insert(build_data).execute()
        if not build_result.data:
            raise HTTPException(status_code=500, detail="Création build Supabase échouée")

        build = dict(build_result.data[0])
        build_id = str(build["id"])

        license_row = await license_manager.create_license(
            build_id=build_id,
            client_email=request.client_email,
            model=request.model,
        )
        license_key = str(license_row["license_key"])

        _supabase().table("electron_builds").update(
            {"license_key": license_key, "build_status": "building"}
        ).eq("id", build_id).execute()

        background_tasks.add_task(
            _compile_in_background,
            build_id=build_id,
            app_name=request.app_name,
            client_name=request.client_name,
            files=files,
            model=request.model,
            license_key=license_key,
            version=request.version,
        )

        return {
            "success": True,
            "build_id": build_id,
            "license_key": license_key,
            "status": "building",
            "message": (
                "Compilation lancée — poll /api/electron/build/{build_id} pour le statut"
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Build error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/build/{build_id}")
async def get_build_status(build_id: str) -> dict[str, Any]:
    """Retourne le statut d'un build en cours."""
    try:
        result = (
            _supabase()
            .table("electron_builds")
            .select("*")
            .eq("id", build_id.strip())
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Build introuvable")

        return dict(result.data)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/builds")
async def list_builds() -> dict[str, list[dict[str, Any]]]:
    """Liste tous les builds clients pour le dashboard CyberForge."""
    try:
        result = (
            _supabase()
            .table("electron_builds")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"builds": [dict(row) for row in (result.data or [])]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/licenses/check")
async def check_license(request: LicenseCheckRequest) -> dict[str, Any]:
    """
    Vérifie si une licence est active.
    Appelé par le .exe client au démarrage (modèle abonnement).
    """
    return await license_manager.check_license(request.license_key)


@router.get("/licenses")
async def list_licenses() -> dict[str, list[dict[str, Any]]]:
    """Liste toutes les licences pour le dashboard CyberForge."""
    licenses = await license_manager.get_all_licenses()
    return {"licenses": licenses}


@router.post("/licenses/deactivate")
async def deactivate_license(request: LicenseDeactivateRequest) -> dict[str, bool]:
    """Désactive une licence (abonnement annulé)."""
    success = await license_manager.deactivate_license(request.license_key)
    return {"success": success}


async def _compile_in_background(
    build_id: str,
    app_name: str,
    client_name: str,
    files: dict[str, str],
    model: str,
    license_key: str,
    version: str,
) -> None:
    """Lance la compilation GitHub Actions en arrière-plan."""
    try:
        result = await electron_compiler.compile(
            app_name=app_name,
            client_name=client_name,
            files=files,
            model=model,
            license_key=license_key,
            version=version,
        )

        github_repo = str(result.get("repo") or "")
        run_id = str(result.get("run_id") or "")

        _supabase().table("electron_builds").update(
            {
                "github_repo": github_repo,
                "github_run_id": run_id,
                "build_status": "building" if run_id else "failed",
            }
        ).eq("id", build_id).execute()

        if not run_id:
            return

        repo_name = github_repo.split("/")[-1]
        for _ in range(40):
            await asyncio.sleep(30)
            status = await electron_compiler.get_build_status(repo_name, run_id)

            if status["status"] == "success":
                _supabase().table("electron_builds").update(
                    {
                        "build_status": "success",
                        "download_url": status.get("download_url"),
                    }
                ).eq("id", build_id).execute()
                logger.info(
                    "Build %s — SUCCESS — %s",
                    build_id,
                    status.get("download_url"),
                )
                return

            if status["status"] == "failed":
                _supabase().table("electron_builds").update(
                    {"build_status": "failed"}
                ).eq("id", build_id).execute()
                logger.error("Build %s — FAILED", build_id)
                return

    except Exception as exc:
        logger.error("Background compile error: %s", exc)
        _supabase().table("electron_builds").update(
            {"build_status": "failed"}
        ).eq("id", build_id).execute()
