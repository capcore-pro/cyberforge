"""
Public booking API for site_reservation projects.

Called by the Vercel Next.js reservation site.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.managed_projects_store import get_managed_projects_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reservation_public"])


def _not_configured() -> HTTPException:
    store = get_managed_projects_store()
    return HTTPException(
        status_code=503,
        detail={
            "message": "Supabase non configuré (SUPABASE_URL + SUPABASE_SECRET_KEY requis).",
            "diagnostics": store.connection_diagnostics(),
        },
    )


async def _get_project_by_slug(slug: str) -> dict[str, Any]:
    store = get_managed_projects_store()
    if not store.is_configured():
        raise _not_configured()
    pid = await store.get_project_id_by_slug(slug=slug, type="site_reservation")
    if not pid:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    row = await store.get_project(pid)
    if not row or row.type != "site_reservation" or row.deleted_at:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return {"id": row.id, "slug": row.slug}


class ServiceRow(BaseModel):
    id: str
    name: str
    duration_min: int
    price_cents: int
    active: bool
    sort: int


@router.get("/reservation/{slug}/services", response_model=list[ServiceRow])
async def list_services(slug: str) -> list[ServiceRow]:
    project = await _get_project_by_slug(slug)
    store = get_managed_projects_store()
    url = f"{store._rest_url()}/reservation_services"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "active": "eq.true",
                "select": "id,name,duration_min,price_cents,active,sort",
                "order": "sort.asc,name.asc",
            },
        )
        if resp.status_code >= 400:
            logger.warning("list_services failed: %s", resp.text)
            raise HTTPException(status_code=502, detail="Supabase error")
        rows = resp.json() if isinstance(resp.json(), list) else []
        return [ServiceRow(**r) for r in rows if isinstance(r, dict)]


class SlotsResponse(BaseModel):
    slots: list[str]  # ISO starts_at


def _parse_iso(dt: str) -> datetime:
    # Accept "2026-05-28T10:00:00Z" or "+00:00"
    if dt.endswith("Z"):
        dt = dt[:-1] + "+00:00"
    parsed = datetime.fromisoformat(dt)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@router.get("/reservation/{slug}/slots", response_model=SlotsResponse)
async def list_slots(
    slug: str,
    service_id: str,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
) -> SlotsResponse:
    project = await _get_project_by_slug(slug)
    store = get_managed_projects_store()

    start = _parse_iso(from_)
    end = _parse_iso(to)
    if end <= start:
        raise HTTPException(status_code=400, detail="Invalid range")
    if end - start > timedelta(days=31):
        raise HTTPException(status_code=400, detail="Range too large")

    # Load service duration
    svc_url = f"{store._rest_url()}/reservation_services"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        rsvc = await client.get(
            svc_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "id": f"eq.{service_id}",
                "project_id": f"eq.{project['id']}",
                "select": "id,duration_min,active",
            },
        )
        if rsvc.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        svc_rows = rsvc.json()
        if not svc_rows:
            raise HTTPException(status_code=404, detail="Service introuvable.")
        svc = svc_rows[0]
        if not svc.get("active", True):
            return SlotsResponse(slots=[])
        duration = int(svc["duration_min"])

    # Weekly availability
    avail_url = f"{store._rest_url()}/reservation_availability"  # noqa: SLF001
    blocks_url = f"{store._rest_url()}/reservation_blocks"  # noqa: SLF001
    res_url = f"{store._rest_url()}/reservations"  # noqa: SLF001

    async with httpx.AsyncClient(timeout=30.0) as client:
        rav = await client.get(
            avail_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "select": "weekday,start_time,end_time",
            },
        )
        if rav.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        av_rows = rav.json() if isinstance(rav.json(), list) else []
        by_wd: dict[int, list[tuple[str, str]]] = {}
        for row in av_rows:
            try:
                wd = int(row["weekday"])
                by_wd.setdefault(wd, []).append((row["start_time"], row["end_time"]))
            except Exception:
                continue

        # Blocks and existing reservations in range
        rbl = await client.get(
            blocks_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "starts_at": f"lt.{end.isoformat()}",
                "ends_at": f"gt.{start.isoformat()}",
                "select": "starts_at,ends_at",
            },
        )
        if rbl.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        blocks = [( _parse_iso(b["starts_at"]), _parse_iso(b["ends_at"]) ) for b in (rbl.json() or [])]

        rres = await client.get(
            res_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "project_id": f"eq.{project['id']}",
                "starts_at": f"lt.{end.isoformat()}",
                "ends_at": f"gt.{start.isoformat()}",
                "status": "eq.confirmed",
                "select": "starts_at,ends_at",
            },
        )
        if rres.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        reservations = [( _parse_iso(b["starts_at"]), _parse_iso(b["ends_at"]) ) for b in (rres.json() or [])]

    step = timedelta(minutes=15)
    dur_td = timedelta(minutes=duration)
    slots: list[str] = []

    cursor = start.replace(second=0, microsecond=0)
    # align to 15 minutes
    minute_mod = cursor.minute % 15
    if minute_mod:
        cursor += timedelta(minutes=(15 - minute_mod))

    while cursor + dur_td <= end:
        wd = cursor.weekday()  # Monday=0 .. Sunday=6
        windows = by_wd.get(wd, [])
        if windows:
            ok_window = False
            for st, en in windows:
                # st/en are "HH:MM:SS"
                st_h, st_m, *_ = st.split(":")
                en_h, en_m, *_ = en.split(":")
                w_start = cursor.replace(hour=int(st_h), minute=int(st_m), second=0, microsecond=0)
                w_end = cursor.replace(hour=int(en_h), minute=int(en_m), second=0, microsecond=0)
                if w_end <= w_start:
                    continue
                if cursor >= w_start and cursor + dur_td <= w_end:
                    ok_window = True
                    break
            if ok_window:
                candidate_start = cursor
                candidate_end = cursor + dur_td
                overlaps = False
                for a, b in blocks + reservations:
                    if candidate_start < b and candidate_end > a:
                        overlaps = True
                        break
                if not overlaps:
                    slots.append(candidate_start.isoformat().replace("+00:00", "Z"))
        cursor += step

    return SlotsResponse(slots=slots)


class ReserveRequest(BaseModel):
    service_id: str
    starts_at: str
    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_email: str = Field(..., min_length=5, max_length=254)
    notes: str | None = Field(default=None, max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class ReserveResponse(BaseModel):
    reservation_id: str
    status: str


@router.post("/reservation/{slug}/reserve", response_model=ReserveResponse)
async def reserve(slug: str, body: ReserveRequest) -> ReserveResponse:
    project = await _get_project_by_slug(slug)
    store = get_managed_projects_store()

    starts = _parse_iso(body.starts_at)
    # Load service duration
    svc_url = f"{store._rest_url()}/reservation_services"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        rsvc = await client.get(
            svc_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "id": f"eq.{body.service_id}",
                "project_id": f"eq.{project['id']}",
                "select": "id,duration_min,active",
            },
        )
        if rsvc.status_code >= 400:
            raise HTTPException(status_code=502, detail="Supabase error")
        svc_rows = rsvc.json()
        if not svc_rows:
            raise HTTPException(status_code=404, detail="Service introuvable.")
        svc = svc_rows[0]
        if not svc.get("active", True):
            raise HTTPException(status_code=400, detail="Service inactif.")
        duration = int(svc["duration_min"])

    ends = starts + timedelta(minutes=duration)

    # Ensure slot is still available by reusing the overlap logic with a narrow window.
    slot_check = await list_slots(
        slug=slug,
        service_id=body.service_id,
        from_=starts.isoformat().replace("+00:00", "Z"),
        to=(starts + timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
    )
    if starts.isoformat().replace("+00:00", "Z") not in slot_check.slots:
        raise HTTPException(status_code=409, detail="Créneau indisponible.")

    url = f"{store._rest_url()}/reservations"  # noqa: SLF001
    payload = {
        "project_id": project["id"],
        "service_id": body.service_id,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "status": "confirmed",
        "notes": body.notes,
    }
    # V1: idempotency is best-effort; we don't persist it yet.
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=store._headers("return=representation"), json=payload)  # noqa: SLF001
        if resp.status_code >= 400:
            logger.warning("reserve failed: %s", resp.text)
            raise HTTPException(status_code=502, detail="Supabase error")
        rows = resp.json()
        row = rows[0] if isinstance(rows, list) and rows else rows
        return ReserveResponse(reservation_id=row["id"], status=row.get("status", "confirmed"))


@router.post("/reservation/{slug}/stripe/webhook")
async def stripe_webhook_stub(slug: str) -> dict[str, str]:
    # V2: implement real Stripe webhook validation + state changes.
    _ = slug
    return {"status": "disabled"}

