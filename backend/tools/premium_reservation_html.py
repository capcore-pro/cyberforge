"""Template premium — réservations (créneaux, noms, dates, statuts)."""

from __future__ import annotations

import json

from tools.premium_base import (
    CYBERFORGE_PREVIEW_MARKER,
    PREMIUM_BASE_CSS,
    escape_html,
    shell_nav_script,
    user_initials,
)

RESERVATION_MARKER = "cf-premium-reservation"


def build_premium_reservation_html(
    *,
    title: str = "Réservations",
    subtitle: str | None = None,
    brand_name: str = "BookTable",
    brand_tag: str = "Gestion des créneaux",
    user_name: str = "Alex Martin",
    user_role: str = "Responsable salle",
    bookings: list[dict[str, str | int]] | None = None,
) -> str:
    from tools.premium_demo_data import RESERVATION_SLOTS

    page_title = escape_html(title)
    sub = escape_html(subtitle or "Planning des tables et créneaux en temps réel.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))

    rows = list(bookings or RESERVATION_SLOTS)
    row_html: list[str] = []
    for idx, b in enumerate(rows[:8]):
        bid = escape_html(str(b.get("id") or idx + 1))
        date = escape_html(str(b.get("date") or ""))
        slot = escape_html(str(b.get("slot") or ""))
        name = escape_html(str(b.get("name") or ""))
        covers = escape_html(str(b.get("covers") or ""))
        status = escape_html(str(b.get("status") or ""))
        note = escape_html(str(b.get("note") or ""))
        active = " active" if idx == 0 else ""
        status_cls = "cf-status-ok" if status == "Confirmée" else (
            "cf-status-warn" if status == "En attente" else "cf-status-muted"
        )
        row_html.append(
            f"""          <tr class="cf-booking-row{active}" data-booking="{bid}">
            <td>{date}</td>
            <td><strong>{slot}</strong></td>
            <td>{name}</td>
            <td>{covers}</td>
            <td><span class="cf-status-pill {status_cls}">{status}</span></td>
            <td style="color:#64748b;font-size:0.8rem;">{note}</td>
          </tr>"""
        )

    first = rows[0] if rows else {}
    detail_name = escape_html(str(first.get("name") or "—"))
    detail_date = escape_html(str(first.get("date") or "—"))
    detail_slot = escape_html(str(first.get("slot") or "—"))
    detail_status = escape_html(str(first.get("status") or "—"))
    detail_covers = escape_html(str(first.get("covers") or "—"))
    detail_note = escape_html(str(first.get("note") or "—"))

    bookings_json = json.dumps(
        {
            str(b.get("id", i + 1)): {
                "name": b.get("name", ""),
                "date": b.get("date", ""),
                "slot": b.get("slot", ""),
                "covers": b.get("covers", ""),
                "status": b.get("status", ""),
                "note": b.get("note", ""),
            }
            for i, b in enumerate(rows)
        },
        ensure_ascii=False,
    )

    table_body = "\n".join(row_html)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {RESERVATION_MARKER} -->
  <style>
{PREMIUM_BASE_CSS}
    .cf-topbar {{
      display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(15,23,42,0.9);
    }}
    .cf-res-grid {{
      display: grid; grid-template-columns: 1fr; gap: 1rem; padding: 1rem;
    }}
    @media (min-width: 900px) {{
      .cf-res-grid {{ grid-template-columns: 1.4fr 0.9fr; }}
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th, td {{ padding: 0.6rem 0.5rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    th {{ color: #64748b; font-size: 0.7rem; text-transform: uppercase; }}
    .cf-booking-row {{ cursor: pointer; }}
    .cf-booking-row:hover {{ background: rgba(255,255,255,0.03); }}
    .cf-booking-row.active {{ background: rgba(99,102,241,0.12); }}
    .cf-status-pill {{
      font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 600;
    }}
    .cf-status-ok {{ background: rgba(74,222,128,0.15); color: #4ade80; }}
    .cf-status-warn {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
    .cf-status-muted {{ background: rgba(148,163,184,0.15); color: #94a3b8; }}
    .cf-detail-label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; }}
    .cf-detail-value {{ color: #f8fafc; margin-bottom: 0.75rem; }}
  </style>
</head>
<body class="{RESERVATION_MARKER}">
  <div class="cf-shell" id="cf-shell">
    <header class="cf-topbar">
      <div class="cf-logo">{initials}</div>
      <div style="flex:1;">
        <div style="font-weight:700;">{brand}</div>
        <div style="font-size:0.75rem;color:#64748b;">{tag} — {page_title}</div>
      </div>
      <div style="text-align:right;font-size:0.8rem;">{user}<br/><span style="color:#64748b;">{role}</span></div>
    </header>
    <p style="padding:0 1rem;color:#64748b;font-size:0.85rem;margin:0;">{sub}</p>
    <div class="cf-res-grid">
      <div class="cf-card" style="overflow-x:auto;">
        <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Créneaux réservés</h3>
        <table>
          <thead>
            <tr><th>Date</th><th>Heure</th><th>Client</th><th>Couverts</th><th>Statut</th><th>Note</th></tr>
          </thead>
          <tbody>
{table_body}
          </tbody>
        </table>
      </div>
      <div class="cf-card" id="cf-booking-detail">
        <h3 style="margin:0 0 1rem;font-size:0.9rem;color:#f8fafc;">Détail réservation</h3>
        <div class="cf-detail-label">Client</div>
        <div class="cf-detail-value" id="d-name">{detail_name}</div>
        <div class="cf-detail-label">Date & créneau</div>
        <div class="cf-detail-value" id="d-datetime">{detail_date} · {detail_slot}</div>
        <div class="cf-detail-label">Couverts</div>
        <div class="cf-detail-value" id="d-covers">{detail_covers}</div>
        <div class="cf-detail-label">Statut</div>
        <div class="cf-detail-value" id="d-status">{detail_status}</div>
        <div class="cf-detail-label">Note</div>
        <div class="cf-detail-value" id="d-note">{detail_note}</div>
        <button type="button" class="cf-btn cf-btn-primary" style="width:100%;margin-top:0.5rem;">Modifier la réservation</button>
      </div>
    </div>
  </div>
  <script>
    var bookings = {bookings_json};
    document.querySelectorAll(".cf-booking-row").forEach(function(row) {{
      row.addEventListener("click", function() {{
        document.querySelectorAll(".cf-booking-row").forEach(function(r) {{ r.classList.remove("active"); }});
        row.classList.add("active");
        var b = bookings[row.getAttribute("data-booking")];
        if (!b) return;
        document.getElementById("d-name").textContent = b.name;
        document.getElementById("d-datetime").textContent = b.date + " · " + b.slot;
        document.getElementById("d-covers").textContent = String(b.covers);
        document.getElementById("d-status").textContent = b.status;
        document.getElementById("d-note").textContent = b.note;
      }});
    }});
  </script>
</body>
</html>"""
