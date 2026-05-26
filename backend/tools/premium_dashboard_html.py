"""Template premium — dashboard analytics (KPIs, graphiques, tableaux)."""

from __future__ import annotations

import re

from tools.premium_base import (
    TEMPLATE_DASHBOARD,
    escape_html,
    premium_footer_html,
    premium_page_wrap,
    sidebar_nav_html,
    unsplash_hero_url,
    user_initials,
)

DASHBOARD_MARKER = "cf-premium-dashboard"


def _parse_kpi_number(value: str) -> tuple[str, str, str]:
    """Extrait nombre, préfixe et suffixe pour compteur animé."""
    raw = str(value).strip()
    m = re.search(r"([\d\s.,]+)", raw)
    num_str = (m.group(1) if m else "0").replace(" ", "").replace(",", ".")
    try:
        num = float(num_str)
        if num == int(num):
            target = str(int(num))
        else:
            target = str(num)
    except ValueError:
        target = "0"
    prefix = raw[: m.start()] if m else ""
    suffix = raw[m.end() :] if m else ""
    return target, prefix, suffix


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
    hero_img = unsplash_hero_url(TEMPLATE_DASHBOARD)

    kpi_list = list(kpis or DASHBOARD_KPIS)
    kpi_html_parts: list[str] = []
    for k in kpi_list[:4]:
        label = escape_html(str(k.get("label") or ""))
        value = str(k.get("value") or "")
        target, prefix, suffix = _parse_kpi_number(value)
        trend = escape_html(str(k.get("trend") or ""))
        up = k.get("up", True)
        trend_color = "#4ade80" if up else "#94a3b8"
        kpi_html_parts.append(
            f"""        <div class="cf-card cf-reveal cf-kpi-card">
          <div class="cf-kpi-label">{label}</div>
          <div class="cf-kpi-value cf-counter" data-target="{escape_html(target)}" data-prefix="{escape_html(prefix)}" data-suffix="{escape_html(suffix)}">0</div>
          <div class="cf-kpi-trend" style="color:{trend_color};">{trend}</div>
        </div>"""
        )
    kpi_html = "\n".join(kpi_html_parts)

    bars = list(chart_bars or DASHBOARD_CHART)
    chart_html = "\n".join(
        f'          <div class="cf-bar cf-reveal" style="height:{int(b.get("height", 50))}%" title="{escape_html(str(b.get("month") or ""))}"></div>'
        for b in bars[:6]
    )

    sector_rows = list(sectors or DASHBOARD_SECTORS)
    table_html = "\n".join(
        f"""            <tr class="cf-reveal"><td>{escape_html(str(s.get("sector") or ""))}</td>
              <td>{escape_html(str(s.get("revenue") or ""))}</td>
              <td style="color:#4ade80;">{escape_html(str(s.get("growth") or ""))}</td>
              <td>{escape_html(str(s.get("share") or ""))}</td></tr>"""
        for s in sector_rows[:6]
    )

    extra_css = """
    .cf-kpi-grid {
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; padding: 1rem;
    }
    @media (min-width: 700px) { .cf-kpi-grid { grid-template-columns: repeat(4, 1fr); } }
    .cf-kpi-value {
      font-family: var(--cf-font-display); font-size: 1.65rem; font-weight: 800;
      color: #f8fafc; margin-top: 0.35rem;
    }
    .cf-kpi-label { font-size: 0.68rem; color: var(--cf-muted); text-transform: uppercase; letter-spacing: 0.06em; }
    .cf-kpi-trend { font-size: 0.78rem; margin-top: 0.35rem; }
    .cf-chart-wrap { padding: 0 1rem 1.25rem; }
    .cf-chart {
      height: 220px; display: flex; align-items: flex-end; gap: 0.55rem;
      padding: 1.25rem; background: var(--cf-surface);
      border-radius: 18px; border: 1px solid rgba(255,255,255,0.08);
    }
    .cf-bar {
      flex: 1; background: linear-gradient(180deg, var(--cf-primary), var(--cf-secondary));
      border-radius: 8px 8px 0 0; min-width: 14px;
      box-shadow: 0 -4px 20px var(--cf-glow);
      transition: transform 0.3s;
    }
    .cf-bar:hover { transform: scaleY(1.05); transform-origin: bottom; }
    .cf-table-wrap { padding: 0 1rem 1rem; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th, td { padding: 0.7rem 0.85rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
    th { color: var(--cf-muted); font-weight: 600; font-size: 0.68rem; text-transform: uppercase; }
    .cf-dash-banner {
      margin: 0 1rem 1rem; border-radius: 16px; overflow: hidden; max-height: 120px;
    }
    .cf-dash-banner img { width: 100%; height: 120px; object-fit: cover; opacity: 0.75; }
    .cf-alert-item {
      padding: 0.85rem; border-radius: 12px; margin-bottom: 0.65rem;
      background: rgba(0,0,0,0.25); border-left: 3px solid var(--cf-primary);
    }
    .cf-report-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    """
    nav_sidebar = sidebar_nav_html(
        (("overview", "Vue d'ensemble"), ("reports", "Rapports"), ("alerts", "Alertes")),
        active="overview",
    )

    body = f"""
  <div class="cf-shell cf-with-sidebar" id="cf-shell">
    <div class="cf-sidebar-backdrop"></div>
    <aside class="cf-sidebar">
      <div style="padding:0 1.25rem 1.25rem;display:flex;gap:0.85rem;align-items:center;">
        <div class="cf-logo">{initials}</div>
        <div><div class="cf-brand-name">{brand}</div><div class="cf-brand-tag">{tag}</div></div>
      </div>
      <nav style="padding:0 0.75rem;" aria-label="Navigation dashboard">
{nav_sidebar}
      </nav>
    </aside>
    <div class="cf-main">
      <header class="cf-topbar cf-reveal">
        <button type="button" class="cf-menu-btn" aria-label="Menu"><span></span><span></span><span></span></button>
        <div style="flex:1;">
          <div id="cf-page-title" style="font-weight:600;font-size:1.05rem;">Vue d'ensemble</div>
          <div style="font-size:0.75rem;color:var(--cf-muted);">{sub}</div>
        </div>
        <button type="button" class="cf-btn cf-btn-primary" style="font-size:0.8rem;padding:0.5rem 1rem;" data-cf-action="nav" data-cf-nav-target="reports">Exporter</button>
        <span style="font-size:0.8rem;margin-left:0.5rem;">{user} · {role}</span>
      </header>
      <div class="cf-dash-banner cf-reveal">
        <img src="{hero_img}" alt="" loading="lazy" />
      </div>
      <div class="cf-app-view active" data-cf-view="overview">
        <div class="cf-kpi-grid">
{kpi_html}
        </div>
        <div class="cf-chart-wrap cf-reveal">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Chiffre d'affaires — 6 derniers mois</h3>
          <div class="cf-chart" role="img" aria-label="Graphique ventes">
{chart_html}
          </div>
        </div>
        <div class="cf-table-wrap">
          <h3 style="margin:0 0 0.85rem;font-size:0.95rem;color:#f8fafc;">Performance par secteur</h3>
          <div class="cf-card" style="padding:0;overflow:hidden;">
          <table>
            <thead><tr><th>Secteur</th><th>CA</th><th>Croissance</th><th>Part</th></tr></thead>
            <tbody>
{table_html}
            </tbody>
          </table>
          </div>
        </div>
      </div>
      <div class="cf-app-view" data-cf-view="reports">
        <div class="cf-card cf-reveal">
          <h3 style="margin:0 0 1rem;color:#f8fafc;">Rapports programmés</h3>
          <div class="cf-report-row"><span>CA mensuel — PDF</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo" data-cf-demo-msg="Rapport PDF envoyé chaque lundi dans votre version CapCore.">Télécharger</button></div>
          <div class="cf-report-row"><span>KPIs équipe — Excel</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo">Exporter</button></div>
          <div class="cf-report-row"><span>Tableau sectoriel</span><button type="button" class="cf-btn cf-btn-ghost" data-cf-action="demo">Aperçu</button></div>
          <button type="button" class="cf-btn cf-btn-primary" style="margin-top:1rem;" data-cf-action="contact">Demander un rapport sur mesure</button>
        </div>
      </div>
      <div class="cf-app-view" data-cf-view="alerts">
        <div class="cf-card cf-reveal">
          <h3 style="margin:0 0 1rem;color:#f8fafc;">Alertes actives</h3>
          <div class="cf-alert-item"><strong>Seuil marge</strong><br/><span style="color:var(--cf-muted);font-size:0.85rem;">Marge sous 18 % sur le segment B2B — il y a 2 h</span></div>
          <div class="cf-alert-item" style="border-color:#fbbf24;"><strong>Pic de trafic</strong><br/><span style="color:var(--cf-muted);font-size:0.85rem;">+34 % de sessions vs baseline — aujourd'hui</span></div>
          <div class="cf-alert-item" style="border-color:#4ade80;"><strong>Objectif atteint</strong><br/><span style="color:var(--cf-muted);font-size:0.85rem;">Quota commercial Q2 validé — hier</span></div>
        </div>
      </div>
{premium_footer_html(brand_name=brand_name, template=TEMPLATE_DASHBOARD)}
    </div>
  </div>"""

    return premium_page_wrap(
        title=title,
        marker=DASHBOARD_MARKER,
        template=TEMPLATE_DASHBOARD,
        extra_css=extra_css,
        body_html=body,
    )
