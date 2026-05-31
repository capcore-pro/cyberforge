"""
SSE — progression temps réel du pipeline LangGraph (Générateur).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agents.pipeline_graph import run_generation_pipeline
from api.routes.coremind import CoreMindRequest, CoreMindRunResponse
from db.supabase_store import PersistenceResult, SupabaseStoreError, get_supabase_store
from tools.codegen_service import CodeGenServiceError
from api.routes.coremind import _codegen_http_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])


def _sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/agents/coremind/run/stream")
async def run_coremind_flow_stream(body: CoreMindRequest) -> StreamingResponse:
    """
    Flow complet avec événements SSE (step_start / step_done / result / error).
    Même résultat final que POST /agents/coremind/run.
    """

    async def event_generator() -> AsyncIterator[str]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_event(event: dict) -> None:
            await queue.put(event)

        async def run_pipeline() -> None:
            try:
                result = await run_generation_pipeline(
                    body.prompt,
                    project_type_hint=body.project_type,
                    generation_mode=body.generation_mode,
                    openhands_enabled=body.openhands_enabled,
                    playwright_enabled=body.playwright_enabled,
                    lighthouse_enabled=body.lighthouse_enabled,
                    research_enabled=body.research_enabled,
                    project_id=body.project_id,
                    inspiration_brief=body.inspiration_brief,
                    personal_project=body.personal_project,
                    pages_project_slug=body.pages_project_slug,
                    project_title=body.project_title,
                    on_event=on_event,
                )
                persistence: PersistenceResult | None = None
                store = get_supabase_store()
                if store.is_configured():
                    try:
                        project_type = body.project_type or result.analysis.project_type
                        persistence = await store.save_generation(
                            body.prompt.strip(),
                            project_type,
                            result,
                        )
                    except SupabaseStoreError as exc:
                        logger.warning("Sauvegarde Supabase ignorée : %s", exc)

                if persistence is not None:
                    from tools.export_demo_persistence import (
                        persist_pipeline_cloudflare_demo,
                    )

                    try:
                        await persist_pipeline_cloudflare_demo(
                            run_result=result,
                            generation_id=persistence.generation_id,
                        )
                    except Exception as exc:
                        logger.warning("Persistance démo ExportAI ignorée : %s", exc)

                payload = CoreMindRunResponse(
                    **result.model_dump(),
                    persistence=persistence,
                )
                await queue.put(
                    {
                        "type": "result",
                        "data": payload.model_dump(mode="json"),
                    }
                )
            except ValueError as exc:
                await queue.put({"type": "error", "detail": str(exc)})
            except CodeGenServiceError as exc:
                http_exc = _codegen_http_error(exc)
                await queue.put(
                    {"type": "error", "detail": http_exc.detail, "status": http_exc.status_code}
                )
            except Exception as exc:
                logger.exception("Pipeline SSE échoué")
                await queue.put({"type": "error", "detail": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_pipeline())
        try:
            yield _sse_line({"type": "pipeline_start"})
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield _sse_line(item)
            yield _sse_line({"type": "pipeline_end"})
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
