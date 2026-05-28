"""
E2E: create site_reservation → wait deployed → seed services+availability → fetch slots → reserve → verify slot disappears.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import os

import httpx
from dotenv import load_dotenv

BASE = (os.environ.get("BASE_URL") or "http://127.0.0.1:8002").rstrip("/")


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def main() -> None:
    load_dotenv("backend/.env", override=False)
    slug = f"resatest-{int(time.time())}"
    prompt = "Site de réservation V1: choisir service + créneau + confirmation."
    c = httpx.Client(timeout=90.0)

    r = c.post(f"{BASE}/api/managed-projects/site-reservation", json={"prompt": prompt, "slug": slug})
    r.raise_for_status()
    pid = r.json()["project"]["id"]
    print("created", slug, pid)

    # Wait deployed
    for _ in range(90):
        row = c.get(f"{BASE}/api/managed-projects/site-reservation/{pid}").json()
        st = row.get("status")
        if st in ("deployed", "failed"):
            print("status", st)
            if st == "failed":
                raise SystemExit(row.get("error_last"))
            break
        time.sleep(2.0)

    # Seed service + availability directly via PostgREST (service role key in backend env, so public API can read).
    # Seed via direct PostgREST using env vars passed to this script:
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        raise SystemExit("Missing SUPABASE_URL + SUPABASE_SECRET_KEY env vars for seeding.")

    rest = f"{supabase_url}/rest/v1"
    headers = {"apikey": supabase_key, "authorization": f"Bearer {supabase_key}", "content-type": "application/json"}

    # Insert one active service
    svc = httpx.post(
        f"{rest}/reservation_services",
        headers={**headers, "prefer": "return=representation"},
        json={
            "project_id": pid,
            "name": "Coupe",
            "duration_min": 30,
            "price_cents": 2500,
            "active": True,
            "sort": 0,
        },
    )
    svc.raise_for_status()
    service_id = svc.json()[0]["id"]
    print("service", service_id)

    # Availability: today weekday 09:00-12:00 UTC
    today = datetime.now(tz=UTC)
    wd = today.weekday()
    av = httpx.post(
        f"{rest}/reservation_availability",
        headers={**headers, "prefer": "return=representation"},
        json={"project_id": pid, "weekday": wd, "start_time": "09:00:00", "end_time": "12:00:00"},
    )
    av.raise_for_status()

    # Fetch slots for next few hours window
    start = today.replace(hour=9, minute=0, second=0, microsecond=0)
    end = today.replace(hour=12, minute=0, second=0, microsecond=0)
    slots = c.get(
        f"{BASE}/api/public/reservation/{slug}/slots",
        params={"service_id": service_id, "from": iso(start), "to": iso(end)},
    )
    slots.raise_for_status()
    data = slots.json()
    first = (data.get("slots") or [None])[0]
    if not first:
        raise SystemExit("No slots returned")
    print("slot", first)

    # Reserve first slot
    rr = c.post(
        f"{BASE}/api/public/reservation/{slug}/reserve",
        json={
            "service_id": service_id,
            "starts_at": first,
            "customer_name": "Test User",
            "customer_email": "test@example.com",
            "notes": "e2e",
        },
    )
    rr.raise_for_status()
    reservation_id = rr.json()["reservation_id"]
    print("reservation", reservation_id)

    # Verify slot disappears
    slots2 = c.get(
        f"{BASE}/api/public/reservation/{slug}/slots",
        params={"service_id": service_id, "from": iso(start), "to": iso(end)},
    )
    slots2.raise_for_status()
    data2 = slots2.json()
    assert first not in (data2.get("slots") or []), "slot should disappear after reservation"
    print("ok")


if __name__ == "__main__":
    main()

