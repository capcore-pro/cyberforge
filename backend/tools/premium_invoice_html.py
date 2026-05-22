"""Template premium — facturation (liste factures, création, TVA)."""

from __future__ import annotations

from tools.premium_base import (
    CYBERFORGE_PREVIEW_MARKER,
    PREMIUM_BASE_CSS,
    escape_attr,
    escape_html,
    shell_nav_script,
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
) -> str:
    page_title = escape_html(title)
    sub = escape_html(subtitle or "Émettez et suivez vos factures en quelques clics.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {INVOICE_MARKER} -->
  <style>
{PREMIUM_BASE_CSS}
    .cf-invoice-layout {{
      display: grid; grid-template-columns: 1fr; gap: 1rem; padding: 1rem;
    }}
    @media (min-width: 960px) {{
      .cf-invoice-layout {{ grid-template-columns: 1fr 1.1fr 0.9fr; }}
    }}
    .cf-topbar {{
      display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }}
    .cf-menu-btn {{
      display: flex; width: 40px; height: 40px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
      color: #fff; cursor: pointer;
    }}
    .cf-inv-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.65rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
      cursor: pointer;
    }}
    .cf-inv-row:hover {{ background: rgba(255,255,255,0.03); }}
    .cf-inv-row.active {{ background: rgba(99,102,241,0.12); }}
    .cf-badge {{
      font-size: 0.65rem; padding: 0.2rem 0.5rem; border-radius: 6px;
      background: rgba(74,222,128,0.15); color: #4ade80;
    }}
    .cf-badge-pending {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
    .cf-form label {{ display: block; font-size: 0.7rem; color: #64748b; margin-bottom: 0.25rem; }}
    .cf-form input, .cf-form select {{
      width: 100%; padding: 0.5rem 0.65rem; margin-bottom: 0.75rem;
      border-radius: 8px; border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.25); color: #e2e8f0;
    }}
    .cf-totals {{ font-size: 0.9rem; }}
    .cf-totals .line {{ display: flex; justify-content: space-between; margin-bottom: 0.4rem; color: #94a3b8; }}
    .cf-totals .grand {{ font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <div class="cf-shell" id="cf-shell">
    <header class="cf-topbar">
      <button type="button" class="cf-menu-btn" aria-label="Menu" style="visibility:hidden">☰</button>
      <div class="cf-logo">{initials}</div>
      <div style="flex:1;">
        <div style="font-weight:700;">{brand}</div>
        <div style="font-size:0.75rem;color:#64748b;">{tag} — {page_title}</div>
      </div>
      <div style="text-align:right;font-size:0.8rem;">{user}<br/><span style="color:#64748b;">{role}</span></div>
    </header>
    <p style="padding:0 1rem;color:#64748b;font-size:0.85rem;margin:0;">{sub}</p>
    <div class="cf-invoice-layout">
      <div class="cf-card">
        <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Factures</h3>
        <div class="cf-inv-row active" data-inv="2026-042">
          <div><strong>FAC-2026-042</strong><br/><span style="font-size:0.75rem;color:#64748b;">Acme Industries</span></div>
          <div><span class="cf-badge">Payée</span><br/>4 560 €</div>
        </div>
        <div class="cf-inv-row" data-inv="2026-043">
          <div><strong>FAC-2026-043</strong><br/><span style="font-size:0.75rem;color:#64748b;">GreenTech SAS</span></div>
          <div><span class="cf-badge cf-badge-pending">En attente</span><br/>2 880 €</div>
        </div>
        <div class="cf-inv-row" data-inv="2026-044">
          <div><strong>FAC-2026-044</strong><br/><span style="font-size:0.75rem;color:#64748b;">Studio Nova</span></div>
          <div><span class="cf-badge cf-badge-pending">Brouillon</span><br/>1 200 €</div>
        </div>
      </div>
      <div class="cf-card cf-form">
        <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Nouvelle facture</h3>
        <label>Client</label>
        <input type="text" value="Acme Industries" id="inv-client" />
        <label>Description</label>
        <input type="text" value="Prestation conseil — Avril 2026" />
        <label>Montant HT (€)</label>
        <input type="number" value="3800" id="inv-ht" />
        <label>Taux TVA</label>
        <select id="inv-tva"><option value="20" selected>20 %</option><option value="10">10 %</option></select>
        <button type="button" class="cf-btn cf-btn-primary" style="width:100%;" id="inv-calc">Calculer les totaux</button>
      </div>
      <div class="cf-card cf-totals" id="inv-totals">
        <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Récapitulatif</h3>
        <div class="line"><span>Total HT</span><span id="t-ht">3 800,00 €</span></div>
        <div class="line"><span>TVA (20 %)</span><span id="t-tva">760,00 €</span></div>
        <div class="line grand"><span>Total TTC</span><span id="t-ttc">4 560,00 €</span></div>
        <button type="button" class="cf-btn cf-btn-ghost" style="width:100%;margin-top:1rem;">Télécharger PDF</button>
      </div>
    </div>
  </div>
  <script>
    function fmt(n) {{ return n.toLocaleString("fr-FR", {{ minimumFractionDigits: 2 }}) + " €"; }}
    function recalc() {{
      var ht = parseFloat(document.getElementById("inv-ht").value) || 0;
      var rate = parseFloat(document.getElementById("inv-tva").value) || 20;
      var tva = ht * rate / 100;
      document.getElementById("t-ht").textContent = fmt(ht);
      document.getElementById("t-tva").textContent = fmt(tva);
      document.getElementById("t-ttc").textContent = fmt(ht + tva);
    }}
    document.getElementById("inv-calc").addEventListener("click", recalc);
    document.getElementById("inv-ht").addEventListener("input", recalc);
    document.getElementById("inv-tva").addEventListener("change", recalc);
    document.querySelectorAll(".cf-inv-row").forEach(function(row) {{
      row.addEventListener("click", function() {{
        document.querySelectorAll(".cf-inv-row").forEach(function(r) {{ r.classList.remove("active"); }});
        row.classList.add("active");
      }});
    }});
  </script>
</body>
</html>"""
