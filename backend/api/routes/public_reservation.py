"""
Public booking API for site_reservation projects.

Called by the Vercel Next.js reservation site.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from db.managed_projects_store import get_managed_projects_store
from stripe_service import StripeServiceError, create_checkout_session, handle_webhook

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
    shop_url = (row.url_production or row.url_preview or "").strip()
    if not shop_url:
        shop_url = f"https://{row.slug}.vercel.app"
    return {
        "id": row.id,
        "slug": row.slug,
        "client_name": (row.title or row.slug or "Hébergement").strip(),
        "demo_url": shop_url,
        "couleur_primaire": "#1D9E75",
    }


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


class ReservationCheckoutResponse(BaseModel):
    reservation_id: str
    checkout_session_id: str
    checkout_url: str


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
                "select": "id,duration_min,price_cents,active",
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
        price_cents = int(svc.get("price_cents") or 0)

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

    nights = max(1, (ends.date() - starts.date()).days) or 1
    total_price = round(price_cents / 100.0, 2) if price_cents > 0 else 0.0
    property_contact = ""
    try:
        auth = await store.get_project_auth(str(project["id"]))
        if auth and auth.client_email:
            property_contact = str(auth.client_email).strip()
    except Exception:
        property_contact = ""

    async def _send_reservation_email() -> None:
        try:
            from agents.email_ai import send_reservation_confirmation

            await send_reservation_confirmation(
                reservation_data={
                    "guest_name": body.customer_name,
                    "guest_email": body.customer_email,
                    "checkin": starts.strftime("%d/%m/%Y %H:%M"),
                    "checkout": ends.strftime("%d/%m/%Y %H:%M"),
                    "nights": nights,
                    "total_price": total_price,
                    "property_contact": property_contact,
                },
                property_name=str(project.get("client_name") or "Hébergement"),
                property_url=str(project.get("demo_url") or ""),
                couleur_primaire=str(project.get("couleur_primaire") or "#1D9E75"),
            )
        except Exception as exc:
            logger.warning("[EmailAI] confirmation réservation ignorée: %s", exc)

    asyncio.create_task(_send_reservation_email())
    return ReserveResponse(reservation_id=row["id"], status=row.get("status", "confirmed"))


@router.post("/reservation/{slug}/checkout", response_model=ReservationCheckoutResponse)
async def checkout_reservation(slug: str, body: ReserveRequest) -> ReservationCheckoutResponse:
    """Crée une réservation en attente de paiement + session Stripe Checkout."""
    project = await _get_project_by_slug(slug)
    store = get_managed_projects_store()

    starts = _parse_iso(body.starts_at)
    svc_url = f"{store._rest_url()}/reservation_services"  # noqa: SLF001
    async with httpx.AsyncClient(timeout=30.0) as client:
        rsvc = await client.get(
            svc_url,
            headers=store._headers(),  # noqa: SLF001
            params={
                "id": f"eq.{body.service_id}",
                "project_id": f"eq.{project['id']}",
                "select": "id,name,duration_min,price_cents,active",
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
        service_name = str(svc.get("name") or "Prestation")
        price_cents = int(svc.get("price_cents") or 0)

    if price_cents <= 0:
        raise HTTPException(
            status_code=400,
            detail="Ce service est gratuit — utilisez /reserve sans paiement.",
        )

    ends = starts + timedelta(minutes=duration)
    slot_check = await list_slots(
        slug=slug,
        service_id=body.service_id,
        from_=starts.isoformat().replace("+00:00", "Z"),
        to=(starts + timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
    )
    if starts.isoformat().replace("+00:00", "Z") not in slot_check.slots:
        raise HTTPException(status_code=409, detail="Créneau indisponible.")

    res_url = f"{store._rest_url()}/reservations"  # noqa: SLF001
    payload = {
        "project_id": project["id"],
        "service_id": body.service_id,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "status": "pending_payment",
        "notes": body.notes,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            res_url,
            headers=store._headers("return=representation"),  # noqa: SLF001
            json=payload,
        )
        if resp.status_code >= 400:
            logger.warning("checkout reserve failed: %s", resp.text)
            raise HTTPException(status_code=502, detail="Supabase error")
        rows = resp.json()
        row = rows[0] if isinstance(rows, list) and rows else rows
        reservation_id = row["id"]

    success_url = (
        f"https://{slug}.vercel.app/success?session_id={{CHECKOUT_SESSION_ID}}"
    )
    cancel_url = f"https://{slug}.vercel.app/"

    try:
        session = create_checkout_session(
            project_id=str(project["id"]),
            items=[
                {
                    "name": service_name,
                    "unit_amount": price_cents,
                    "quantity": 1,
                }
            ],
            customer_email=body.customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            mode="payment",
            client_reference_id=reservation_id,
            metadata={
                "reservation_id": reservation_id,
                "slug": slug,
                "service_id": body.service_id,
            },
        )
    except StripeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session_id = str(session.id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.patch(
            res_url,
            headers=store._headers(),  # noqa: SLF001
            params={"id": f"eq.{reservation_id}"},
            json={"stripe_checkout_session_id": session_id},
        )

    return ReservationCheckoutResponse(
        reservation_id=reservation_id,
        checkout_session_id=session_id,
        checkout_url=str(session.url),
    )


@router.post("/reservation/{slug}/stripe/webhook")
async def stripe_webhook(
    slug: str,
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    project = await _get_project_by_slug(slug)
    payload = await request.body()

    try:
        result = handle_webhook(
            payload,
            stripe_signature or "",
            project_id=str(project["id"]),
        )
    except StripeServiceError as exc:
        detail = str(exc)
        status = 400 if "invalide" in detail.lower() else 502
        raise HTTPException(status_code=status, detail=detail) from exc

    if result.get("type") != "checkout.session.completed":
        return result

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return result

    obj = (event.get("data") or {}).get("object") or {}
    metadata = obj.get("metadata") or {}
    reservation_id = str(metadata.get("reservation_id") or "").strip()
    session_id = str(obj.get("id") or "").strip()

    store = get_managed_projects_store()
    res_url = f"{store._rest_url()}/reservations"  # noqa: SLF001
    patch: dict[str, Any] = {"status": "confirmed"}
    if obj.get("customer_details"):
        patch["customer_email"] = obj["customer_details"].get("email")
        patch["customer_name"] = obj["customer_details"].get("name")

    params: dict[str, str] = {}
    if reservation_id:
        params["id"] = f"eq.{reservation_id}"
    elif session_id:
        params["stripe_checkout_session_id"] = f"eq.{session_id}"
    else:
        return result

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            res_url,
            headers=store._headers(),  # noqa: SLF001
            params=params,
            json=patch,
        )
        if r.status_code >= 400:
            logger.warning("reservation webhook patch failed: %s", r.text[:200])
    return {"status": "ok", "type": "checkout.session.completed"}

