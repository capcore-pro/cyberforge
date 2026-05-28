"""
Admin API for ecommerce catalog management (used by CyberForge UI).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.managed_projects_store import get_managed_projects_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ecommerce_admin"])


def _not_configured() -> HTTPException:
    store = get_managed_projects_store()
    return HTTPException(
        status_code=503,
        detail={
            "message": "Supabase non configuré (SUPABASE_URL + SUPABASE_SECRET_KEY requis).",
            "diagnostics": store.connection_diagnostics(),
        },
    )


async def _project_id_for_slug(slug: str) -> str:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    pid = await store.get_project_id_by_slug(slug=slug, type="ecommerce")
    if not pid:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return pid


class ProductIn(BaseModel):
    sku: str | None = Field(default=None, max_length=120)
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    price_cents: int = Field(..., ge=0, le=10_000_000)
    currency: str = Field(default="eur", max_length=3)
    image_url: str | None = Field(default=None, max_length=2000)
    active: bool = True
    sort: int = 0
    stock_qty: int | None = Field(default=None, ge=0, le=1_000_000)


@router.get("/admin/ecommerce/{slug}/products")
async def admin_list_products(slug: str) -> list[dict[str, Any]]:
    pid = await _project_id_for_slug(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{pid}",
                "select": "*",
                "order": "sort.asc,name.asc",
            },
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        data = r.json()
        return data if isinstance(data, list) else []


@router.post("/admin/ecommerce/{slug}/products")
async def admin_create_product(slug: str, body: ProductIn) -> dict[str, Any]:
    pid = await _project_id_for_slug(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    payload = body.model_dump()
    payload["project_id"] = pid
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            headers=store._headers("return=representation"),  # noqa: SLF001
            json=payload,
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=r.text[:300])
        rows = r.json()
        row = rows[0] if isinstance(rows, list) and rows else rows
        return row if isinstance(row, dict) else {"ok": True}


class ProductPatch(BaseModel):
    sku: str | None = Field(default=None, max_length=120)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    currency: str | None = Field(default=None, max_length=3)
    image_url: str | None = Field(default=None, max_length=2000)
    active: bool | None = None
    sort: int | None = None
    stock_qty: int | None = Field(default=None, ge=0, le=1_000_000)


@router.patch("/admin/ecommerce/{slug}/products/{product_id}")
async def admin_update_product(slug: str, product_id: str, body: ProductPatch) -> dict[str, Any]:
    pid = await _project_id_for_slug(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        return {"updated": False}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            url,
            headers=store._headers("return=representation"),  # noqa: SLF001
            params={"id": f"eq.{product_id}", "project_id": f"eq.{pid}"},
            json=patch,
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=r.text[:300])
        rows = r.json()
        row = rows[0] if isinstance(rows, list) and rows else rows
        return row if isinstance(row, dict) else {"updated": True}


@router.delete("/admin/ecommerce/{slug}/products/{product_id}")
async def admin_delete_product(slug: str, product_id: str) -> dict[str, bool]:
    pid = await _project_id_for_slug(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/ecommerce_products"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(
            url,
            headers=store._headers(),  # noqa: SLF001
            params={"id": f"eq.{product_id}", "project_id": f"eq.{pid}"},
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=r.text[:300])
        return {"deleted": True}

