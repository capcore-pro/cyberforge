"""Template premium — facturation (liste factures, création, TVA)."""

from __future__ import annotations

import json

from tools.premium_base import (
    TEMPLATE_FACTURATION,
    escape_html,
    header_tabs_html,
    premium_footer_html,
    premium_header_html,
    premium_page_wrap,
    unsplash_hero_url,
    user_initials,
)

INVOICE_MARKER = "cf-premium-invoice"


def build_premium_invoice_html(
    *,
    title: str = "Facturation",
    subtitle: str | None = None,
    brand_name: str = "BillForge",
    brand_tag: str = "Comptabilité simplifiée",
    user_name: str = "Alex Martin",
    user_role: str = "Responsable finance",
    invoices: list[dict[str, str | float | int]] | None = None,
) -> str:
    from tools.premium_demo_data import INVOICES

    page_title = escape_html(title)
    sub = escape_html(subtitle or "Émettez et suivez vos factures en quelques clics.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))
    hero_img = unsplash_hero_url(TEMPLATE_FACTURATION)

    inv_list = list(invoices or INVOICES)
    row_html: list[str] = []
    inv_map: dict[str, dict[str, object]] = {}
    for idx, inv in enumerate(inv_list[:6]):
        iid = str(inv.get("id") or idx)
        number = escape_html(str(inv.get("number") or f"FAC-{iid}"))
        client = escape_html(str(inv.get("client") or ""))
        ht = float(inv.get("ht") or 0)
        ttc = ht * 1.2
        status = escape_html(str(inv.get("status") or ""))
        badge = escape_html(str(inv.get("badge_class") or "cf-badge"))
        active = " active" if idx == 0 else ""
        row_html.append(
            f"""        <div class="cf-inv-row{active} cf-reveal" data-inv="{escape_html(iid)}">
          <div><strong>{number}</strong><br/><span style="font-size:0.75rem;color:var(--cf-muted);">{client}</span></div>
          <div><span class="{badge}">{status}</span><br/>{escape_html(f"{ttc:,.0f}".replace(",", " "))} € TTC</div>
        </div>"""
        )
        inv_map[iid] = {
            "client": str(inv.get("client") or ""),
            "ht": ht,
            "number": str(inv.get("number") or ""),
        }

    first = inv_list[0] if inv_list else {}
    first_ht = float(first.get("ht") or 3800)
    first_tva = first_ht * 0.2
    first_ttc = first_ht + first_tva
    first_client = escape_html(str(first.get("client") or "Client démo"))
    inv_json = json.dumps(inv_map, ensure_ascii=False)
    rows = "\n".join(row_html)

    extra_css = """
    .cf-invoice-layout {
      display: grid; grid-template-columns: 1fr; gap: 1.25rem; padding: 1rem;
    }
    @media (min-width: 960px) { .cf-invoice-layout { grid-template-columns: 1fr 1.1fr 0.9fr; } }
    .cf-inv-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
      cursor: pointer; transition: background 0.2s;
    }
    .cf-inv-row:hover { background: rgba(255,255,255,0.03); }
    .cf-inv-row.active { background: color-mix(in srgb, var(--cf-primary) 14%, transparent); }
    .cf-badge {
      font-size: 0.65rem; padding: 0.25rem 0.55rem; border-radius: 8px;
      background: rgba(74,222,128,0.15); color: #4ade80; font-weight: 600;
    }
    .cf-badge-pending { background: rgba(251,191,36,0.15); color: #fbbf24; }
    .cf-badge-overdue { background: rgba(248,113,113,0.15); color: #f87171; }
    .cf-form label { display: block; font-size: 0.7rem; color: var(--cf-muted); margin-bottom: 0.3rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .cf-form input, .cf-form select {
      width: 100%; padding: 0.6rem 0.75rem; margin-bottom: 0.85rem;
      border-radius: 10px; border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.3); color: #e2e8f0; font-family: var(--cf-font-body);
    }
    .cf-totals .line { display: flex; justify-content: space-between; margin-bottom: 0.45rem; color: var(--cf-muted); }
    .cf-totals .grand {
      font-size: 1.35rem; font-weight: 800; color: #f8fafc; margin-top: 0.65rem;
      font-family: var(--cf-font-display);
    }
    .cf-invoice-banner { margin: 0 1rem; border-radius: 14px; overflow: hidden; max-height: 100px; }
    .cf-invoice-banner img { width: 100%; height: 100px; object-fit: cover; opacity: 0.8; }
    .cf-kpi-row {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
      padding: 0 1rem 1rem;
    }
    .cf-kpi-pill {
      text-align: center; padding: 0.85rem; border-radius: 14px;
      background: color-mix(in srgb, var(--cf-primary) 12%, transparent);
      border: 1px solid color-mix(in srgb, var(--cf-primary) 22%, transparent);
    }
    .cf-kpi-pill .v { font-family: var(--cf-font-display); font-size: 1.25rem; font-weight: 700; color: #f8fafc; }
    .cf-kpi-pill .l { font-size: 0.65rem; color: var(--cf-muted); text-transform: uppercase; }
    """

    body = f"""
  <div class="cf-shell" id="cf-shell">
{premium_header_html(
    brand_name=brand_name,
    brand_tag=brand_tag or "Comptabilité simplifiée",
    initials=initials,
    template=TEMPLATE_FACTURATION,
    nav_links=(
        ("#view-liste", "Factures"),
        ("#view-creer", "Émettre"),
        ("#cf-footer", "Contact"),
    ),
    cta_label="Nouvelle facture",
    cta_action="nav",
    cta_nav_target="creer",
    show_menu=True,
)}
{header_tabs_html((("liste", "Factures"), ("creer", "Émettre"), ("export", "Exports")), active="liste")}
    <p class="cf-reveal" style="padding:0 1.25rem;color:var(--cf-muted);font-size:0.9rem;margin:0;">{sub}</p>
    <div class="cf-invoice-banner cf-reveal">
      <img src="{hero_img}" alt="" loading="lazy" />
    </div>
    <div class="cf-app-view active" data-cf-view="liste" id="view-liste">
      <div class="cf-kpi-row cf-reveal">
        <div class="cf-kpi-pill"><div class="v cf-counter" data-target="24">0</div><div class="l">Factures ce mois</div></div>
        <div class="cf-kpi-pill"><div class="v cf-counter" data-target="48250" data-suffix=" €">0</div><div class="l">Encaissé</div></div>
        <div class="cf-kpi-pill"><div class="v cf-counter" data-target="3">0</div><div class="l">En retard</div></div>
      </div>
      <div class="cf-invoice-layout">
        <div class="cf-card cf-reveal">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Factures récentes</h3>
{rows}
        </div>
        <div class="cf-card cf-form cf-reveal" id="nouvelle">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Aperçu émission</h3>
          <p style="color:var(--cf-muted);font-size:0.85rem;margin:0;">Sélectionnez une facture ou passez à l'onglet Émettre.</p>
        </div>
        <div class="cf-card cf-totals cf-reveal">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Récapitulatif</h3>
          <div class="line"><span>Total HT</span><span id="t-ht">{first_ht:,.2f} €</span></div>
          <div class="line"><span>TVA (20 %)</span><span id="t-tva">{first_tva:,.2f} €</span></div>
          <div class="line grand"><span>Total TTC</span><span id="t-ttc" class="cf-counter" data-target="{int(first_ttc)}">{first_ttc:,.0f} €</span></div>
        </div>
      </div>
    </div>
    <div class="cf-app-view" data-cf-view="creer" id="view-creer">
      <div class="cf-invoice-layout" style="grid-template-columns:1fr;">
        <div class="cf-card cf-form cf-reveal">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Nouvelle facture</h3>
          <label>Client</label>
          <input type="text" value="{first_client}" id="inv-client" />
          <label>Description</label>
          <input type="text" value="Prestation conseil — Mai 2026" />
          <label>Montant HT (€)</label>
          <input type="number" value="{int(first_ht)}" id="inv-ht" />
          <label>Taux TVA</label>
          <select id="inv-tva"><option value="20" selected>20 %</option><option value="10">10 %</option></select>
          <button type="button" class="cf-btn cf-btn-primary" style="width:100%;" id="inv-calc">Calculer les totaux</button>
        </div>
        <div class="cf-card cf-totals cf-reveal" id="inv-totals">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Récapitulatif</h3>
          <div class="line"><span>Total HT</span><span id="t-ht-2">{first_ht:,.2f} €</span></div>
          <div class="line"><span>TVA (20 %)</span><span id="t-tva-2">{first_tva:,.2f} €</span></div>
          <div class="line grand"><span>Total TTC</span><span id="t-ttc-2">{first_ttc:,.0f} €</span></div>
          <button type="button" class="cf-btn cf-btn-primary" style="width:100%;margin-top:1rem;" data-cf-action="contact">Envoyer au client</button>
        </div>
      </div>
    </div>
    <div class="cf-app-view" data-cf-view="export">
      <div class="cf-card cf-reveal" style="margin:1rem;">
        <h3 style="margin:0 0 1rem;color:#f8fafc;">Exports comptables</h3>
        <p style="color:var(--cf-muted);font-size:0.9rem;">Journal des ventes, FEC et rapprochement bancaire.</p>
        <button type="button" class="cf-btn cf-btn-ghost" style="margin-top:1rem;" data-cf-action="demo" data-cf-demo-msg="Export FEC disponible dans votre version CapCore.">Télécharger PDF</button>
        <button type="button" class="cf-btn cf-btn-primary" style="margin-top:0.75rem;" data-cf-action="contact">Configurer avec CapCore</button>
      </div>
    </div>
{premium_footer_html(brand_name=brand_name, template=TEMPLATE_FACTURATION)}
  </div>
  <script>
    var invoices = {inv_json};
    function fmt(n) {{ return n.toLocaleString("fr-FR", {{ minimumFractionDigits: 2 }}) + " €"; }}
    function setTotals(ht, tva, ttc) {{
      var fmtHt = fmt(ht), fmtTva = fmt(tva), fmtTtc = fmt(ttc);
      ["t-ht", "t-ht-2"].forEach(function(id) {{
        var el = document.getElementById(id);
        if (el) el.textContent = fmtHt;
      }});
      ["t-tva", "t-tva-2"].forEach(function(id) {{
        var el = document.getElementById(id);
        if (el) el.textContent = fmtTva;
      }});
      ["t-ttc", "t-ttc-2"].forEach(function(id) {{
        var el = document.getElementById(id);
        if (el) {{
          el.setAttribute("data-target", String(Math.round(ttc)));
          el.textContent = fmtTtc;
        }}
      }});
    }}
    function recalc() {{
      var ht = parseFloat(document.getElementById("inv-ht").value) || 0;
      var rate = parseFloat(document.getElementById("inv-tva").value) || 20;
      var tva = ht * rate / 100;
      setTotals(ht, tva, ht + tva);
    }}
    document.getElementById("inv-calc").addEventListener("click", recalc);
    document.getElementById("inv-ht").addEventListener("input", recalc);
    document.getElementById("inv-tva").addEventListener("change", recalc);
    document.querySelectorAll(".cf-inv-row").forEach(function(row) {{
      row.addEventListener("click", function() {{
        document.querySelectorAll(".cf-inv-row").forEach(function(r) {{ r.classList.remove("active"); }});
        row.classList.add("active");
        var inv = invoices[row.getAttribute("data-inv")];
        if (inv) {{
          document.getElementById("inv-client").value = inv.client;
          document.getElementById("inv-ht").value = inv.ht;
          recalc();
        }}
      }});
    }});
  </script>"""

    return premium_page_wrap(
        title=title,
        marker=INVOICE_MARKER,
        template=TEMPLATE_FACTURATION,
        extra_css=extra_css,
        body_html=body,
    )
