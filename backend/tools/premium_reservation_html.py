"""Template premium — réservations (créneaux, noms, dates, statuts)."""

from __future__ import annotations

import json

from tools.premium_base import (
    TEMPLATE_RESERVATION,
    escape_html,
    header_tabs_html,
    premium_footer_html,
    premium_header_html,
    premium_page_wrap,
    unsplash_hero_url,
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
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))
    hero_img = unsplash_hero_url(TEMPLATE_RESERVATION, vertical="restaurant")

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
        status_cls = (
            "cf-status-ok"
            if status == "Confirmée"
            else ("cf-status-warn" if status == "En attente" else "cf-status-muted")
        )
        row_html.append(
            f"""          <tr class="cf-booking-row{active} cf-reveal" data-booking="{bid}">
            <td>{date}</td>
            <td><strong>{slot}</strong></td>
            <td>{name}</td>
            <td>{covers}</td>
            <td><span class="cf-status-pill {status_cls}">{status}</span></td>
            <td style="color:var(--cf-muted);font-size:0.8rem;">{note}</td>
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

    extra_css = """
    .cf-res-grid { display: grid; grid-template-columns: 1fr; gap: 1.25rem; padding: 1rem; }
    @media (min-width: 900px) { .cf-res-grid { grid-template-columns: 1.45fr 0.95fr; } }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th, td { padding: 0.65rem 0.55rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
    th { color: var(--cf-muted); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .cf-booking-row { cursor: pointer; transition: background 0.2s; }
    .cf-booking-row:hover { background: rgba(255,255,255,0.03); }
    .cf-booking-row.active { background: color-mix(in srgb, var(--cf-primary) 14%, transparent); }
    .cf-status-pill { font-size: 0.68rem; padding: 0.25rem 0.55rem; border-radius: 8px; font-weight: 600; }
    .cf-status-ok { background: rgba(74,222,128,0.15); color: #4ade80; }
    .cf-status-warn { background: rgba(251,191,36,0.15); color: #fbbf24; }
    .cf-status-muted { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .cf-detail-label { font-size: 0.68rem; color: var(--cf-muted); text-transform: uppercase; }
    .cf-detail-value { color: #f8fafc; margin-bottom: 0.85rem; font-weight: 500; }
    .cf-res-banner { margin: 0 1rem 1rem; border-radius: 16px; overflow: hidden; max-height: 160px; }
    .cf-res-banner img { width: 100%; height: 160px; object-fit: cover; }
    .cf-res-stats {
      display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;
      padding: 0 1rem 1rem;
    }
    .cf-res-stat { text-align: center; min-width: 90px; }
    .cf-res-stat .v { font-family: var(--cf-font-display); font-size: 1.5rem; font-weight: 800; color: #f8fafc; }
    .cf-res-stat .l { font-size: 0.72rem; color: var(--cf-muted); }
    """

    tabs = header_tabs_html(
        (("planning", "Planning"), ("stats", "Statistiques"), ("contact", "Contact")),
        active="planning",
    )
    body = f"""
  <div class="cf-shell" id="cf-shell">
{premium_header_html(
    brand_name=brand_name,
    brand_tag=brand_tag or "Gestion des créneaux",
    initials=initials,
    template=TEMPLATE_RESERVATION,
    nav_links=(
        ("#view-planning", "Planning"),
        ("#view-stats", "Statistiques"),
        ("#cf-footer", "Contact"),
    ),
    cta_label="Nouvelle réservation",
    cta_action="nav",
    cta_nav_target="planning",
)}
{tabs}
    <p class="cf-reveal" style="padding:0 1.25rem;color:var(--cf-muted);font-size:0.9rem;margin:0;">{sub}</p>
    <div class="cf-res-banner cf-reveal">
      <img src="{hero_img}" alt="Salle restaurant" loading="lazy" />
    </div>
    <div class="cf-app-view active" data-cf-view="planning" id="view-planning">
    <div class="cf-res-stats cf-reveal">
      <div class="cf-res-stat"><div class="v cf-counter" data-target="86">0</div><div class="l">Couverts ce soir</div></div>
      <div class="cf-res-stat"><div class="v cf-counter" data-target="12">0</div><div class="l">Réservations</div></div>
      <div class="cf-res-stat"><div class="v cf-counter" data-target="94" data-suffix="%">0</div><div class="l">Taux remplissage</div></div>
    </div>
    <div class="cf-res-grid">
      <div class="cf-card cf-reveal" style="overflow-x:auto;">
        <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Créneaux réservés</h3>
        <table>
          <thead>
            <tr><th>Date</th><th>Heure</th><th>Client</th><th>Couverts</th><th>Statut</th><th>Note</th></tr>
          </thead>
          <tbody>
{table_body}
          </tbody>
        </table>
      </div>
      <div class="cf-card cf-reveal" id="cf-booking-detail">
        <h3 style="margin:0 0 1rem;font-size:0.95rem;color:#f8fafc;">Détail réservation</h3>
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
        <button type="button" class="cf-btn cf-btn-primary" style="width:100%;margin-top:0.5rem;" data-cf-action="demo" data-cf-demo-msg="Modification enregistrée dans votre version CapCore.">Modifier la réservation</button>
      </div>
    </div>
    </div>
    <div class="cf-app-view" data-cf-view="stats" id="view-stats">
      <div class="cf-card cf-reveal" style="margin:1rem;">
        <h3 style="margin:0 0 1rem;color:#f8fafc;">Statistiques salle</h3>
        <p style="color:var(--cf-muted);margin:0 0 1rem;">Taux de remplissage moyen : <strong style="color:#f8fafc;">87 %</strong> · No-show : <strong style="color:#fbbf24;">4 %</strong></p>
        <p style="color:var(--cf-muted);margin:0;">Rotation moyenne : 1h42 · Panier moyen : 48 €</p>
        <button type="button" class="cf-btn cf-btn-primary" style="margin-top:1.25rem;" data-cf-action="contact">Optimiser avec CapCore</button>
      </div>
    </div>
    <div class="cf-app-view" data-cf-view="contact">
      <div class="cf-card cf-reveal" style="margin:1rem;text-align:center;">
        <h3 style="margin:0 0 0.75rem;color:#f8fafc;">Parler à CapCore</h3>
        <p style="color:var(--cf-muted);margin:0 0 1.25rem;">Déploiement réservation en ligne, site et CRM pour votre établissement.</p>
        <button type="button" class="cf-btn cf-btn-primary" data-cf-action="contact">Ouvrir le formulaire de contact</button>
      </div>
    </div>
{premium_footer_html(brand_name=brand_name, template=TEMPLATE_RESERVATION)}
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
  </script>"""

    return premium_page_wrap(
        title=title,
        marker=RESERVATION_MARKER,
        template=TEMPLATE_RESERVATION,
        extra_css=extra_css,
        body_html=body,
    )
