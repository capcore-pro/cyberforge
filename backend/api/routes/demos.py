"""
Routes démos client — création de liens partagés (usage interne / générateur).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from db.demos_store import (
    DemoDuration,
    DemoPayload,
    SupabaseStoreError,
    get_demos_store,
)
from tools.demo_preview_html import build_demo_preview_html

router = APIRouter(tags=["demos"])


class DemoFileInput(BaseModel):
    path: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., max_length=500_000)


class CreateDemoRequest(BaseModel):
    duration: DemoDuration
    title: str | None = Field(default=None, max_length=200)
    files: list[DemoFileInput] = Field(..., min_length=1)
    stack: list[str] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=4000)
    project_type: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=500_000)
    generation_id: str | None = None


class CreateDemoResponse(BaseModel):
    id: str
    token: str
    password: str
    url: str
    expires_at: str
    duration_hours: int
    title: str


def _public_demo_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_public_url.rstrip("/")
    return f"{base}/demo/{token}"


def _http_error_from_supabase(exc: SupabaseStoreError, route: str) -> HTTPException:
    detail = exc.to_http_detail()
    detail["route"] = route
    status = 502
    if detail.get("status_code") == 401:
        status = 401
    return HTTPException(status_code=status, detail=detail)


@router.post("/demos", response_model=CreateDemoResponse)
async def create_client_demo(body: CreateDemoRequest) -> CreateDemoResponse:
    """Crée une démo client avec mot de passe temporaire et date d'expiration."""
    store = get_demos_store()
    if not store.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Supabase non configuré — impossible de créer une démo.",
                "hint": "Configurez SUPABASE_URL et SUPABASE_SECRET_KEY.",
            },
        )

    files = [{"path": f.path.strip(), "content": f.content} for f in body.files]
    if not files:
        raise HTTPException(status_code=422, detail="Au moins un fichier est requis.")

    title = (body.title or "").strip() or "Démo CyberForge"
    try:
        preview_html = build_demo_preview_html(
            files,
            title=title,
            code=body.code,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Impossible de générer l'aperçu HTML : {exc}",
        ) from exc

    payload = DemoPayload(
        preview_html=preview_html,
        summary=body.summary,
        project_type=body.project_type,
    )

    try:
        created = await store.create_demo(
            title=title,
            payload=payload,
            duration=body.duration,
            generation_id=body.generation_id,
        )
    except SupabaseStoreError as exc:
        raise _http_error_from_supabase(exc, "POST /api/demos") from exc

    return CreateDemoResponse(
        id=created.id,
        token=created.token,
        password=created.password,
        url=_public_demo_url(created.token),
        expires_at=created.expires_at,
        duration_hours=created.duration_hours,
        title=created.title,
    )
