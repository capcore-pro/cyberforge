"""Persistance Supabase — table cms_content."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings
from db.supabase_store import (
    SupabaseStore,
    SupabaseStoreError,
    _raise_for_status,
    _raise_transport_error,
)

logger = logging.getLogger(__name__)

CmsBlockType = Literal["text", "image", "color", "url"]


class CmsContentRow(BaseModel):
    id: str
    project_id: str
    block_key: str
    block_type: str
    value: Any = Field(default_factory=dict)
    updated_at: str | None = None


class CmsContentStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self._base = SupabaseStore(settings=settings)

    def is_configured(self) -> bool:
        return self._base.is_configured()

    def _rest_url(self) -> str:
        return self._base._rest_url()  # noqa: SLF001

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        return self._base._headers(prefer)  # noqa: SLF001

    async def list_blocks(self, project_id: str) -> list[CmsContentRow]:
        if not self.is_configured():
            return []
        url = f"{self._rest_url()}/cms_content"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={
                    "project_id": f"eq.{project_id}",
                    "select": "*",
                    "order": "block_key.asc",
                },
            )
            _raise_for_status(resp, "list_cms_content", "GET", url, self._base)
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [CmsContentRow(**row) for row in data if isinstance(row, dict)]

    async def upsert_blocks(
        self,
        project_id: str,
        blocks: list[dict[str, Any]],
    ) -> list[CmsContentRow]:
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        if not blocks:
            return await self.list_blocks(project_id)

        now = datetime.now(tz=UTC).isoformat()
        rows: list[CmsContentRow] = []
        url = f"{self._rest_url()}/cms_content"
        async with httpx.AsyncClient(timeout=30.0) as client:
            for block in blocks:
                block_key = str(block.get("block_key", "")).strip()
                block_type = str(block.get("block_type", "text")).strip()
                value = block.get("value")
                if not block_key:
                    continue
                payload = {
                    "project_id": project_id,
                    "block_key": block_key,
                    "block_type": block_type,
                    "value": value if value is not None else {},
                    "updated_at": now,
                }
                try:
                    resp = await client.post(
                        url,
                        headers=self._headers("resolution=merge-duplicates,return=representation"),
                        params={"on_conflict": "project_id,block_key"},
                        json=payload,
                    )
                except httpx.HTTPError as exc:
                    _raise_transport_error(exc, "upsert_cms_content", "POST", url, self._base)
                _raise_for_status(resp, "upsert_cms_content", "POST", url, self._base)
                data = resp.json()
                row = data[0] if isinstance(data, list) and data else data
                if isinstance(row, dict):
                    rows.append(CmsContentRow(**row))
        return rows

    async def blocks_as_dict(self, project_id: str) -> dict[str, dict[str, Any]]:
        rows = await self.list_blocks(project_id)
        return {
            row.block_key: {
                "block_type": row.block_type,
                "value": row.value,
                "updated_at": row.updated_at,
            }
            for row in rows
        }


@lru_cache
def get_cms_content_store() -> CmsContentStore:
    return CmsContentStore(settings=get_settings())


def reset_cms_content_store() -> None:
    get_cms_content_store.cache_clear()
