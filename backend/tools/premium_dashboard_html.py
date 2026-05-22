"""Template premium — dashboard analytics (KPIs, graphiques, tableaux)."""

from __future__ import annotations

from tools.premium_base import (
    CYBERFORGE_PREVIEW_MARKER,
    PREMIUM_BASE_CSS,
    escape_html,
    shell_nav_script,
    user_initials,
)

DASHBOARD_MARKER = "cf-premium-dashboard"


def build_premium_dashboard_html(
    *,
    title: str = "Analytics",
    subtitle: str | None = None,
    brand_name: str = "InsightHub",
    brand_tag: str = "Business Intelligence",
    user_name: str = "Alex Martin",
    user_role: str = "Data Lead",
    kpis: list[dict[str, str | bool]] | None = None,
    chart_bars: list[dict[str, str | int]] | None = None,
    sectors: list[dict[str, str]] | None = None,
) -> str:
    from tools.premium_demo_data import (
        DASHBOARD_CHART,
        DASHBOARD_KPIS,
        DASHBOARD_SECTORS,
    )

    page_title = escape_html(title)
    sub = escape_html(subtitle or "Vue consolidée de vos indicateurs clés.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    user = escape_html(user_name)
    role = escape_html(user_role)
    initials = escape_html(user_initials(user_name))

    kpi_list = list(kpis or DASHBOARD_KPIS)
    kpi_html = "\n".join(
        f"""        <div class="cf-card"><div class="cf-kpi-label">{escape_html(str(k.get("label") or ""))}</div>
          <div class="cf-kpi-value">{escape_html(str(k.get("value") or ""))}</div>
          <div class="cf-kpi-trend" style="color:{'#4ade80' if k.get('up', True) else '#94a3b8'};">{escape_html(str(k.get("trend") or ""))}</div></div>"""
        for k in kpi_list[:4]
    )

    bars = list(chart_bars or DASHBOARD_CHART)
    chart_html = "\n".join(
        f'          <div class="cf-bar" style="height:{int(b.get("height", 50))}%" title="{escape_html(str(b.get("month") or ""))}"></div>'
        for b in bars[:6]
    )

    sector_rows = list(sectors or DASHBOARD_SECTORS)
    table_html = "\n".join(
        f"""            <tr><td>{escape_html(str(s.get("sector") or ""))}</td>
              <td>{escape_html(str(s.get("revenue") or ""))}</td>
              <td style="color:#4ade80;">{escape_html(str(s.get("growth") or ""))}</td>
              <td>{escape_html(str(s.get("share") or ""))}</td></tr>"""
        for s in sector_rows[:6]
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {DASHBOARD_MARKER} -->
  <style>
{PREMIUM_BASE_CSS}
    .cf-with-sidebar .cf-sidebar {{
      display: none; position: fixed; left: 0; top: 0; bottom: 0; width: min(240px, 85vw);
      background: #111827; border-right: 1px solid rgba(255,255,255,0.06);
      padding: 1rem 0; transform: translateX(-100%); z-index: 50;
    }}
    .cf-shell.cf-nav-open .cf-sidebar {{ display: block; transform: translateX(0); }}
    .cf-sidebar-backdrop {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 40; }}
    .cf-shell.cf-nav-open .cf-sidebar-backdrop {{ display: block; }}
    .cf-menu-btn {{
      display: flex; width: 40px; height: 40px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
      color: #fff; cursor: pointer;
    }}
    .cf-topbar {{
      display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }}
    .cf-kpi-grid {{
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;
      padding: 1rem;
    }}
    @media (min-width: 700px) {{ .cf-kpi-grid {{ grid-template-columns: repeat(4, 1fr); }} }}
    .cf-kpi-value {{ font-size: 1.5rem; font-weight: 700; color: #f8fafc; }}
    .cf-kpi-label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; }}
    .cf-kpi-trend {{ font-size: 0.75rem; color: #4ade80; margin-top: 0.25rem; }}
    .cf-chart-wrap {{ padding: 0 1rem 1rem; }}
    .cf-chart {{
      height: 200px; display: flex; align-items: flex-end; gap: 0.5rem;
      padding: 1rem; background: rgba(15,23,42,0.6); border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .cf-bar {{
      flex: 1; background: linear-gradient(180deg, #6366f1, #4338ca);
      border-radius: 6px 6px 0 0; min-width: 12px;
    }}
    .cf-table-wrap {{ padding: 0 1rem 2rem; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th, td {{ padding: 0.65rem 0.75rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    th {{ color: #64748b; font-weight: 600; font-size: 0.7rem; text-transform: uppercase; }}
  </style>
</head>
<body class="{DASHBOARD_MARKER}">
  <div class="cf-shell cf-with-sidebar" id="cf-shell">
    <div class="cf-sidebar-backdrop"></div>
    <aside class="cf-sidebar">
      <div style="padding:0 1rem 1rem;display:flex;gap:0.75rem;align-items:center;">
        <div class="cf-logo">{initials}</div>
        <div><div style="font-weight:700;">{brand}</div><div style="font-size:0.7rem;color:#64748b;">{tag}</div></div>
      </div>
    </aside>
    <div class="cf-main">
      <header class="cf-topbar">
        <button type="button" class="cf-menu-btn" aria-label="Menu">☰</button>
        <div style="flex:1;">
          <div style="font-weight:600;">{page_title}</div>
          <div style="font-size:0.75rem;color:#64748b;">{sub}</div>
        </div>
        <span style="font-size:0.8rem;">{user} · {role}</span>
      </header>
      <div class="cf-kpi-grid">
{kpi_html}
      </div>
      <div class="cf-chart-wrap">
        <h3 style="margin:0 0 0.75rem;padding:0 0.25rem;font-size:0.9rem;color:#f8fafc;">Chiffre d'affaires — 6 derniers mois</h3>
        <div class="cf-chart" role="img" aria-label="Graphique ventes">
{chart_html}
        </div>
      </div>
      <div class="cf-table-wrap">
        <h3 style="margin:0 0 0.75rem;font-size:0.9rem;color:#f8fafc;">Performance par secteur</h3>
        <table>
          <thead><tr><th>Secteur</th><th>CA</th><th>Croissance</th><th>Part</th></tr></thead>
          <tbody>
{table_html}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  <script>{shell_nav_script()}</script>
</body>
</html>"""
