"""Template premium — CRM (contacts, fiche client, pipeline)."""

from __future__ import annotations

import json

from tools.premium_base import (
    TEMPLATE_CRM,
    escape_html,
    premium_footer_html,
    premium_page_wrap,
    sidebar_nav_html,
    unsplash_hero_url,
    user_initials,
)

CRM_MARKER = "cf-premium-crm"


def build_premium_crm_html(
    *,
    title: str = "CRM Pro",
    subtitle: str | None = None,
    brand_name: str = "RelateCRM",
    brand_tag: str = "Pipeline commercial",
    user_name: str = "Alex Martin",
    user_role: str = "Account Executive",
    contacts: list[dict[str, str]] | None = None,
    pipeline: list[dict[str, str]] | None = None,
) -> str:
    from tools.premium_demo_data import CRM_PIPELINE

    page_title = escape_html(title)
    sub = escape_html(subtitle or "Gérez contacts, opportunités et relances.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))
    hero_img = unsplash_hero_url(TEMPLATE_CRM)

    rows = contacts or [
        {
            "id": "1",
            "company": brand_name,
            "person": "Marie Dupont",
            "status": "Prospect",
            "email": "marie.dupont@demo.fr",
            "role_line": "Marie Dupont — Directrice achats",
        },
        {
            "id": "2",
            "company": "GreenTech SAS",
            "person": "Paul Martin",
            "status": "Client",
            "email": "p.martin@greentech.fr",
            "role_line": "Paul Martin — CTO",
        },
        {
            "id": "3",
            "company": "Studio Nova",
            "person": "Léa Bernard",
            "status": "Perdu",
            "email": "lea@studio-nova.fr",
            "role_line": "Léa Bernard — Fondatrice",
        },
    ]

    contact_items: list[str] = []
    details_map: dict[str, dict[str, str]] = {}
    for idx, row in enumerate(rows[:5]):
        cid = str(row.get("id") or idx + 1)
        company = escape_html(str(row.get("company") or "Compte"))
        person = escape_html(str(row.get("person") or "Contact"))
        status = escape_html(str(row.get("status") or "À suivre"))
        email = escape_html(str(row.get("email") or "contact@demo.fr"))
        role_line = escape_html(
            str(row.get("role_line") or f"{row.get('person', 'Contact')} — {status}")
        )
        active = " active" if idx == 0 else ""
        contact_items.append(
            f"""          <div class="cf-contact{active} cf-reveal" data-contact="{escape_html(cid)}">
            <div style="font-weight:600;">{company}</div>
            <div style="font-size:0.75rem;color:var(--cf-muted);">{person} · {status}</div>
          </div>"""
        )
        details_map[cid] = {
            "company": str(row.get("company") or company),
            "contact": str(row.get("role_line") or role_line),
            "email": str(row.get("email") or email),
            "deal_value": str(row.get("deal_value") or ""),
        }

    first = rows[0]
    d_company = escape_html(str(first.get("company") or brand_name))
    d_contact = escape_html(str(first.get("role_line") or first.get("person") or user_name))
    d_email = escape_html(str(first.get("email") or "contact@demo.fr"))
    d_deal = escape_html(str(first.get("deal_value") or "18 400"))

    pipe_rows = list(pipeline or CRM_PIPELINE)
    pipeline_html = "\n".join(
        f"""            <div class="cf-pipe-col cf-reveal"><div class="cf-pipe-title">{escape_html(str(p.get("stage") or ""))}</div>
              <div class="cf-deal" style="border-color:{escape_html(str(p.get("color") or "#2563eb"))};">{escape_html(str(p.get("deal") or ""))}</div></div>"""
        for p in pipe_rows[:4]
    )

    contacts_html = "\n".join(contact_items)
    details_json = json.dumps(details_map, ensure_ascii=False)

    extra_css = """
    .cf-crm-hero-img {
      margin: 0 1rem 1rem; border-radius: 16px; overflow: hidden; max-height: 140px;
    }
    .cf-crm-hero-img img { width: 100%; height: 140px; object-fit: cover; opacity: 0.85; }
    .cf-crm-grid { display: grid; grid-template-columns: 1fr; gap: 1.25rem; }
    @media (min-width: 900px) { .cf-crm-grid { grid-template-columns: 280px 1fr 1fr; } }
    .cf-contact {
      padding: 0.7rem 0.85rem; border-radius: 12px; cursor: pointer;
      border: 1px solid transparent; margin-bottom: 0.4rem;
      transition: background 0.2s, border-color 0.2s;
    }
    .cf-contact:hover { background: rgba(255,255,255,0.04); }
    .cf-contact.active {
      background: color-mix(in srgb, var(--cf-primary) 16%, transparent);
      border-color: color-mix(in srgb, var(--cf-primary) 35%, transparent);
    }
    .cf-pipeline { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.65rem; }
    @media (min-width: 600px) { .cf-pipeline { grid-template-columns: repeat(4, 1fr); } }
    .cf-pipe-col {
      background: rgba(0,0,0,0.25); border-radius: 12px; padding: 0.65rem; min-height: 130px;
    }
    .cf-pipe-title { font-size: 0.68rem; text-transform: uppercase; color: var(--cf-muted); margin-bottom: 0.5rem; letter-spacing: 0.06em; }
    .cf-deal {
      background: var(--cf-surface); border-radius: 10px; padding: 0.55rem;
      font-size: 0.8rem; margin-bottom: 0.4rem; border-left: 3px solid var(--cf-primary);
    }
    .cf-detail-label { font-size: 0.68rem; color: var(--cf-muted); text-transform: uppercase; letter-spacing: 0.05em; }
    .cf-detail-value { color: #f8fafc; margin-bottom: 0.85rem; font-weight: 500; }
    .cf-kpi-strip {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem;
    }
    .cf-kpi-mini { text-align: center; padding: 0.75rem; border-radius: 12px;
      background: color-mix(in srgb, var(--cf-primary) 10%, transparent);
      border: 1px solid color-mix(in srgb, var(--cf-primary) 20%, transparent);
    }
    .cf-kpi-mini .val { font-family: var(--cf-font-display); font-size: 1.35rem; font-weight: 700; color: #f8fafc; }
    .cf-kpi-mini .lbl { font-size: 0.65rem; color: var(--cf-muted); text-transform: uppercase; }
    .cf-report-list { list-style: none; margin: 0; padding: 0; }
    .cf-report-list li {
      padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
      display: flex; justify-content: space-between; align-items: center; gap: 0.75rem;
    }
    """
    nav_sidebar = sidebar_nav_html(
        (("contacts", "Contacts"), ("pipeline", "Pipeline"), ("reports", "Rapports")),
        active="contacts",
    )

    body = f"""
  <div class="cf-shell cf-with-sidebar" id="cf-shell">
    <div class="cf-sidebar-backdrop" aria-hidden="true"></div>
    <aside class="cf-sidebar">
      <div style="padding:0 1.25rem 1.25rem;display:flex;gap:0.85rem;align-items:center;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:1rem;">
        <div class="cf-logo">{initials}</div>
        <div><div class="cf-brand-name">{brand}</div><div class="cf-brand-tag">{tag}</div></div>
      </div>
      <nav style="padding:0 0.75rem;" aria-label="Navigation CRM">
{nav_sidebar}
      </nav>
    </aside>
    <div class="cf-main">
      <header class="cf-topbar cf-reveal">
        <button type="button" class="cf-menu-btn" aria-label="Menu"><span></span><span></span><span></span></button>
        <div style="flex:1;min-width:0;">
          <div id="cf-page-title" style="font-weight:600;font-size:1.05rem;">Contacts</div>
          <div style="font-size:0.75rem;color:var(--cf-muted);">{sub}</div>
        </div>
        <button type="button" class="cf-btn cf-btn-primary" style="padding:0.5rem 1rem;font-size:0.8rem;" data-cf-action="contact">Nouveau contact</button>
        <div style="text-align:right;font-size:0.8rem;flex-shrink:0;">
          <div>{user}</div><div style="color:var(--cf-muted);">{role}</div>
        </div>
      </header>
      <div class="cf-crm-hero-img cf-reveal">
        <img src="{hero_img}" alt="" loading="lazy" />
      </div>
      <div class="cf-app-view active" data-cf-view="contacts">
        <div class="cf-kpi-strip cf-reveal">
          <div class="cf-kpi-mini"><div class="val cf-counter" data-target="127">0</div><div class="lbl">Contacts</div></div>
          <div class="cf-kpi-mini"><div class="val cf-counter" data-target="34" data-prefix="€" data-suffix="k">0</div><div class="lbl">Pipeline</div></div>
          <div class="cf-kpi-mini"><div class="val cf-counter" data-target="89" data-suffix="%">0</div><div class="lbl">Taux closing</div></div>
        </div>
        <div class="cf-crm-grid">
          <div class="cf-card cf-reveal">
            <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Contacts</h3>
{contacts_html}
          </div>
          <div class="cf-card cf-reveal" id="cf-client-detail">
            <h3 style="margin:0 0 1rem;font-size:0.95rem;color:#f8fafc;">Fiche client</h3>
            <div class="cf-detail-label">Entreprise</div>
            <div class="cf-detail-value" id="d-company">{d_company}</div>
            <div class="cf-detail-label">Contact</div>
            <div class="cf-detail-value" id="d-contact">{d_contact}</div>
            <div class="cf-detail-label">Email</div>
            <div class="cf-detail-value" id="d-email">{d_email}</div>
            <div class="cf-detail-label">Valeur opportunité</div>
            <div class="cf-detail-value" id="d-deal" style="color:#4ade80;font-size:1.15rem;">{d_deal} €</div>
            <button type="button" class="cf-btn cf-btn-primary" style="width:100%;margin-top:0.5rem;" data-cf-action="contact">Planifier un appel</button>
          </div>
          <div class="cf-card cf-reveal">
            <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Pipeline</h3>
            <div class="cf-pipeline">
{pipeline_html}
            </div>
          </div>
        </div>
      </div>
      <div class="cf-app-view" data-cf-view="pipeline">
        <div class="cf-card cf-reveal" style="margin-bottom:1rem;">
          <h3 style="margin:0 0 1rem;color:#f8fafc;">Pipeline commercial</h3>
          <div class="cf-pipeline">
{pipeline_html}
          </div>
        </div>
        <button type="button" class="cf-btn cf-btn-primary" data-cf-action="contact">Ajouter une opportunité</button>
      </div>
      <div class="cf-app-view" data-cf-view="reports">
        <div class="cf-card cf-reveal">
          <h3 style="margin:0 0 1rem;color:#f8fafc;">Rapports & exports</h3>
          <ul class="cf-report-list">
            <li><span>Pipeline — synthèse mensuelle</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo" data-cf-demo-msg="Export PDF généré dans votre version CapCore.">PDF</button></li>
            <li><span>Activité commerciale</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo" data-cf-demo-msg="Export Excel disponible sur mesure.">Excel</button></li>
            <li><span>Prévisions trimestrielles</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo">Voir</button></li>
          </ul>
        </div>
      </div>
{premium_footer_html(brand_name=brand_name, template=TEMPLATE_CRM)}
    </div>
  </div>
  <script>
    var details = {details_json};
    document.querySelectorAll(".cf-contact").forEach(function(el) {{
      el.addEventListener("click", function() {{
        document.querySelectorAll(".cf-contact").forEach(function(c) {{ c.classList.remove("active"); }});
        el.classList.add("active");
        var d = details[el.getAttribute("data-contact")];
        if (d) {{
          document.getElementById("d-company").textContent = d.company;
          document.getElementById("d-contact").textContent = d.contact;
          if (d.email) document.getElementById("d-email").textContent = d.email;
          if (d.deal_value) document.getElementById("d-deal").setAttribute("data-target", d.deal_value.replace(/[^0-9]/g, ""));
        }}
      }});
    }});
  </script>"""

    return premium_page_wrap(
        title=title,
        marker=CRM_MARKER,
        template=TEMPLATE_CRM,
        extra_css=extra_css,
        body_html=body,
        extra_scripts="",
    )
