"""Template premium — CRM (contacts, fiche client, pipeline)."""

from __future__ import annotations

import json

from tools.premium_base import (
    CYBERFORGE_PREVIEW_MARKER,
    PREMIUM_BASE_CSS,
    escape_html,
    shell_nav_script,
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

    rows = contacts or [
        {
            "id": "1",
            "company": brand_name,
            "person": "Marie Dupont",
            "status": "Lead chaud",
            "email": "marie.dupont@demo.fr",
            "role_line": "Marie Dupont — Directrice achats",
        },
        {
            "id": "2",
            "company": "GreenTech SAS",
            "person": "Paul Martin",
            "status": "Négociation",
            "email": "p.martin@greentech.fr",
            "role_line": "Paul Martin — CTO",
        },
        {
            "id": "3",
            "company": "Studio Nova",
            "person": "Léa Bernard",
            "status": "Qualification",
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
            f"""          <div class="cf-contact{active}" data-contact="{escape_html(cid)}">
            <div style="font-weight:600;">{company}</div>
            <div style="font-size:0.75rem;color:#64748b;">{person} · {status}</div>
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
    d_deal = escape_html(str(first.get("deal_value") or "18 400 €"))

    pipe_rows = list(pipeline or CRM_PIPELINE)
    pipeline_html = "\n".join(
        f"""            <div class="cf-pipe-col"><div class="cf-pipe-title">{escape_html(str(p.get("stage") or ""))}</div>
              <div class="cf-deal" style="border-color:{escape_html(str(p.get("color") or "#6366f1"))};">{escape_html(str(p.get("deal") or ""))}</div></div>"""
        for p in pipe_rows[:4]
    )

    contacts_html = "\n".join(contact_items)
    details_json = json.dumps(details_map, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {CRM_MARKER} -->
  <style>
{PREMIUM_BASE_CSS}
    .cf-with-sidebar {{ display: block; }}
    .cf-sidebar {{
      display: none; position: fixed; top: 0; left: 0; bottom: 0; z-index: 50;
      width: min(260px, 88vw); flex-direction: column; padding: 1rem 0;
      background: linear-gradient(180deg, #111827, #0f172a);
      border-right: 1px solid rgba(255,255,255,0.06);
      transform: translateX(-100%); transition: transform 0.25s;
    }}
    .cf-shell.cf-nav-open .cf-sidebar {{ display: flex; transform: translateX(0); }}
    .cf-sidebar-backdrop {{
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 40;
    }}
    .cf-shell.cf-nav-open .cf-sidebar-backdrop {{ display: block; }}
    .cf-menu-btn {{
      display: flex; width: 40px; height: 40px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
      color: #e2e8f0; cursor: pointer; font-size: 1.2rem;
    }}
    .cf-topbar {{
      height: 56px; display: flex; align-items: center; gap: 0.75rem;
      padding: 0 1rem; border-bottom: 1px solid rgba(255,255,255,0.06);
      background: rgba(15,23,42,0.9);
    }}
    .cf-main {{ padding: 1rem; }}
    .cf-crm-grid {{
      display: grid; grid-template-columns: 1fr; gap: 1rem;
    }}
    @media (min-width: 900px) {{
      .cf-crm-grid {{ grid-template-columns: 280px 1fr 1fr; }}
    }}
    .cf-contact {{
      padding: 0.65rem 0.75rem; border-radius: 10px; cursor: pointer;
      border: 1px solid transparent; margin-bottom: 0.35rem;
    }}
    .cf-contact:hover {{ background: rgba(255,255,255,0.04); }}
    .cf-contact.active {{
      background: rgba(99,102,241,0.15); border-color: rgba(129,140,248,0.3);
    }}
    .cf-pipeline {{
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem;
    }}
    @media (min-width: 600px) {{ .cf-pipeline {{ grid-template-columns: repeat(4, 1fr); }} }}
    .cf-pipe-col {{
      background: rgba(0,0,0,0.2); border-radius: 10px; padding: 0.5rem;
      min-height: 120px;
    }}
    .cf-pipe-title {{ font-size: 0.7rem; text-transform: uppercase; color: #64748b; margin-bottom: 0.5rem; }}
    .cf-deal {{
      background: rgba(15,23,42,0.9); border-radius: 8px; padding: 0.5rem;
      font-size: 0.8rem; margin-bottom: 0.35rem; border-left: 3px solid #6366f1;
    }}
    .cf-detail-label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; }}
    .cf-detail-value {{ color: #f8fafc; margin-bottom: 0.75rem; }}
  </style>
</head>
<body class="{CRM_MARKER}">
  <div class="cf-shell cf-with-sidebar" id="cf-shell">
    <div class="cf-sidebar-backdrop" aria-hidden="true"></div>
    <aside class="cf-sidebar">
      <div style="padding:0 1rem 1rem;display:flex;gap:0.75rem;align-items:center;">
        <div class="cf-logo">{initials}</div>
        <div><div style="font-weight:700;color:#f8fafc;">{brand}</div><div style="font-size:0.7rem;color:#64748b;">{tag}</div></div>
      </div>
      <nav style="padding:0 0.75rem;font-size:0.875rem;">
        <div style="padding:0.5rem 0.75rem;color:#a5b4fc;background:rgba(99,102,241,0.15);border-radius:8px;">Contacts</div>
        <div style="padding:0.5rem 0.75rem;color:#94a3b8;">Pipeline</div>
        <div style="padding:0.5rem 0.75rem;color:#94a3b8;">Rapports</div>
      </nav>
    </aside>
    <div class="cf-main">
      <header class="cf-topbar">
        <button type="button" class="cf-menu-btn" aria-label="Menu">☰</button>
        <div style="flex:1;">
          <div style="font-weight:600;">{page_title}</div>
          <div style="font-size:0.75rem;color:#64748b;">{sub}</div>
        </div>
        <div style="text-align:right;font-size:0.8rem;">
          <div>{user}</div><div style="color:#64748b;">{role}</div>
        </div>
      </header>
      <div class="cf-crm-grid" style="margin-top:1rem;">
        <div class="cf-card">
          <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Contacts</h3>
{contacts_html}
        </div>
        <div class="cf-card" id="cf-client-detail">
          <h3 style="margin:0 0 1rem;font-size:0.9rem;color:#f8fafc;">Fiche client</h3>
          <div class="cf-detail-label">Entreprise</div>
          <div class="cf-detail-value" id="d-company">{d_company}</div>
          <div class="cf-detail-label">Contact</div>
          <div class="cf-detail-value" id="d-contact">{d_contact}</div>
          <div class="cf-detail-label">Email</div>
          <div class="cf-detail-value" id="d-email">{d_email}</div>
          <div class="cf-detail-label">Valeur opportunité</div>
          <div class="cf-detail-value" id="d-deal" style="color:#4ade80;">{d_deal}</div>
          <button type="button" class="cf-btn cf-btn-primary" style="width:100%;margin-top:0.5rem;">Planifier un appel</button>
        </div>
        <div class="cf-card">
          <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Pipeline</h3>
          <div class="cf-pipeline">
{pipeline_html}
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
{shell_nav_script()}
    var details = {details_json};
    var contacts = document.querySelectorAll(".cf-contact");
    contacts.forEach(function(el) {{
      el.addEventListener("click", function() {{
        contacts.forEach(function(c) {{ c.classList.remove("active"); }});
        el.classList.add("active");
        var d = details[el.getAttribute("data-contact")];
        if (d) {{
          document.getElementById("d-company").textContent = d.company;
          document.getElementById("d-contact").textContent = d.contact;
          if (d.email) document.getElementById("d-email").textContent = d.email;
          if (d.deal_value) document.getElementById("d-deal").textContent = d.deal_value;
        }}
      }});
    }});
  </script>
</body>
</html>"""
