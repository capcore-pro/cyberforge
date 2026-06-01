"""Téléchargement ZIP extension (pipeline générateur)."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from tools.extension_pipeline import _ARTIFACT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])


@router.get("/pipeline/extension-artifact/{project_id}")
async def download_pipeline_extension_artifact(project_id: str) -> Response:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", project_id)[:80] or "extension"
    path = _ARTIFACT_DIR / f"{safe}.zip"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archive extension introuvable.")
    data = path.read_bytes()
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.zip"',
        },
    )
