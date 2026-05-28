"""Styles et helpers partagés — templates premium CyberForge (v5)."""

from __future__ import annotations

from tools.demo_preview_html import escape_attr, escape_html

CYBERFORGE_PREVIEW_MARKER = "cf-preview:v5-premium"
CAPCORE_CONTACT_EMAIL = "capcore.pro@gmail.com"

# Palettes par type de template
TEMPLATE_CRM = "crm"
TEMPLATE_LANDING = "landing"
TEMPLATE_DASHBOARD = "dashboard"
TEMPLATE_FACTURATION = "facturation"
TEMPLATE_TASKFLOW = "taskflow"
TEMPLATE_RESERVATION = "reservation"

_PALETTES: dict[str, dict[str, str]] = {
    TEMPLATE_CRM: {
        "primary": "#2563eb",
        "secondary": "#0ea5e9",
        "bg": "#0c1222",
        "surface": "rgba(15, 28, 52, 0.88)",
        "glow": "rgba(37, 99, 235, 0.28)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
    TEMPLATE_LANDING: {
        "primary": "#7c3aed",
        "secondary": "#c084fc",
        "bg": "#0a0614",
        "surface": "rgba(30, 20, 55, 0.85)",
        "glow": "rgba(124, 58, 237, 0.35)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
    TEMPLATE_DASHBOARD: {
        "primary": "#22d3ee",
        "secondary": "#6366f1",
        "bg": "#030712",
        "surface": "rgba(10, 15, 30, 0.92)",
        "glow": "rgba(34, 211, 238, 0.22)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
    TEMPLATE_FACTURATION: {
        "primary": "#059669",
        "secondary": "#34d399",
        "bg": "#061410",
        "surface": "rgba(12, 32, 26, 0.9)",
        "glow": "rgba(5, 150, 105, 0.28)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
    TEMPLATE_TASKFLOW: {
        "primary": "#6366f1",
        "secondary": "#22d3ee",
        "bg": "#0b0f1a",
        "surface": "rgba(15, 23, 42, 0.88)",
        "glow": "rgba(99, 102, 241, 0.32)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
    TEMPLATE_RESERVATION: {
        "primary": "#d97706",
        "secondary": "#fbbf24",
        "bg": "#120c06",
        "surface": "rgba(32, 22, 12, 0.9)",
        "glow": "rgba(217, 119, 6, 0.28)",
        "font_display": '"Syne", sans-serif',
        "font_body": '"Space Grotesk", sans-serif',
    },
}

# Images Unsplash (CDN public, pas de clé API)
_UNSPLASH: dict[str, str] = {
    "crm": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1200&q=80&auto=format&fit=crop",
    "landing": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&q=80&auto=format&fit=crop",
    "dashboard": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80&auto=format&fit=crop",
    "facturation": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80&auto=format&fit=crop",
    "taskflow": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80&auto=format&fit=crop",
    "reservation": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&q=80&auto=format&fit=crop",
    "restaurant": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80&auto=format&fit=crop",
    "marketing": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&q=80&auto=format&fit=crop",
    "realestate": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1200&q=80&auto=format&fit=crop",
    "artisan": "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?w=1200&q=80&auto=format&fit=crop",
    "beauty": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=1200&q=80&auto=format&fit=crop",
    "fitness": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200&q=80&auto=format&fit=crop",
}

PREMIUM_BASE_CSS = """
    *, *::before, *::after { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--cf-font-body);
      font-size: 15px;
      line-height: 1.6;
      color: var(--cf-text);
      background: var(--cf-bg);
      -webkit-font-smoothing: antialiased;
    }
    h1, h2, h3, .cf-display {
      font-family: var(--cf-font-display);
      letter-spacing: -0.03em;
    }
    a { color: var(--cf-primary); text-decoration: none; transition: color 0.2s; }
    a:hover { color: var(--cf-secondary); }
    img { max-width: 100%; height: auto; display: block; }
    .cf-shell { min-height: 100vh; width: 100%; max-width: 100vw; overflow-x: hidden; }
    .cf-reveal { opacity: 0; transform: translateY(28px); }
    .cf-reveal.cf-in {
      opacity: 1;
      transform: translateY(0);
      transition: opacity 700ms ease, transform 700ms cubic-bezier(.2,.9,.2,1);
    }
    .cf-btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 0.45rem;
      padding: 0.65rem 1.35rem; border-radius: 12px; font-weight: 600; font-size: 0.9rem;
      border: none; cursor: pointer;
      transition: transform 0.2s cubic-bezier(.34,1.56,.64,1), box-shadow 0.2s, background 0.2s;
      font-family: var(--cf-font-body);
    }
    .cf-btn-primary {
      background: linear-gradient(135deg, var(--cf-primary), color-mix(in srgb, var(--cf-primary) 72%, #1e1b4b));
      color: #fff;
      box-shadow: 0 8px 28px var(--cf-glow);
    }
    @media (hover:hover) and (pointer:fine) {
      .cf-btn-primary:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 12px 36px var(--cf-glow);
      }
    }
    .cf-btn-primary:active { transform: translateY(0) scale(0.98); }
    .cf-btn-ghost {
      background: rgba(255,255,255,0.06);
      color: var(--cf-text);
      border: 1px solid rgba(255,255,255,0.14);
    }
    .cf-btn-ghost:hover {
      background: color-mix(in srgb, var(--cf-primary) 14%, transparent);
      border-color: color-mix(in srgb, var(--cf-primary) 35%, transparent);
    }
    .cf-card {
      background: var(--cf-surface);
      border: 1px solid rgba(255,255,255,0.09);
      border-radius: 18px;
      padding: 1.35rem 1.5rem;
      box-shadow: 0 4px 24px rgba(0,0,0,0.22), 0 1px 0 rgba(255,255,255,0.04) inset;
      transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
    }
    @media (hover:hover) and (pointer:fine) {
      .cf-card:hover {
        border-color: color-mix(in srgb, var(--cf-primary) 28%, transparent);
        box-shadow: 0 12px 40px rgba(0,0,0,0.28), 0 0 0 1px color-mix(in srgb, var(--cf-primary) 12%, transparent);
      }
    }

    :focus-visible {
      outline: 2px solid color-mix(in srgb, var(--cf-secondary) 70%, transparent);
      outline-offset: 2px;
    }

    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after { animation: none !important; transition: none !important; }
      .cf-reveal { opacity: 1 !important; transform: none !important; }
    }
    .cf-logo {
      width: 44px; height: 44px; border-radius: 14px;
      background: linear-gradient(135deg, var(--cf-primary), var(--cf-secondary));
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 0.8rem; color: #fff;
      box-shadow: 0 8px 24px var(--cf-glow);
      flex-shrink: 0;
    }
    .cf-site-header {
      display: flex; align-items: center; justify-content: space-between; gap: 1rem;
      padding: 0.85rem 1.25rem;
      border-bottom: 1px solid rgba(255,255,255,0.07);
      background: color-mix(in srgb, var(--cf-bg) 82%, transparent);
      backdrop-filter: blur(16px);
      position: sticky; top: 0; z-index: 50;
    }
    .cf-brand-block { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
    .cf-brand-name { font-weight: 700; font-size: 1.05rem; color: #f8fafc; }
    .cf-brand-tag { font-size: 0.72rem; color: var(--cf-muted); margin-top: 0.1rem; }
    .cf-nav-desktop {
      display: none; align-items: center; gap: 1.5rem;
      font-size: 0.875rem; font-weight: 500; color: var(--cf-muted);
    }
    .cf-nav-desktop a:hover { color: #f8fafc; text-decoration: none; }
    .cf-header-actions { display: flex; align-items: center; gap: 0.65rem; }
    .cf-menu-btn {
      display: flex; flex-direction: column; justify-content: center; align-items: center;
      width: 44px; height: 44px; border-radius: 12px; gap: 5px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.05);
      cursor: pointer; padding: 0; flex-shrink: 0;
      transition: background 0.2s, border-color 0.2s;
    }
    .cf-menu-btn span {
      display: block; width: 20px; height: 2px; background: #e2e8f0;
      border-radius: 2px; transition: transform 0.3s, opacity 0.3s;
    }
    .cf-shell.cf-nav-open .cf-menu-btn span:nth-child(1) {
      transform: translateY(7px) rotate(45deg);
    }
    .cf-shell.cf-nav-open .cf-menu-btn span:nth-child(2) { opacity: 0; }
    .cf-shell.cf-nav-open .cf-menu-btn span:nth-child(3) {
      transform: translateY(-7px) rotate(-45deg);
    }
    .cf-mobile-nav {
      display: none; flex-direction: column; gap: 0.25rem;
      padding: 0.75rem 1.25rem 1rem;
      background: var(--cf-surface);
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .cf-shell.cf-nav-open .cf-mobile-nav { display: flex; }
    .cf-mobile-nav a {
      padding: 0.65rem 0.5rem; color: #cbd5e1; font-weight: 500;
      border-radius: 8px;
    }
    .cf-mobile-nav a:hover {
      background: color-mix(in srgb, var(--cf-primary) 12%, transparent);
      text-decoration: none;
    }
    .cf-site-footer {
      margin-top: auto;
      padding: 2.5rem 1.25rem 2rem;
      border-top: 1px solid rgba(255,255,255,0.08);
      background: linear-gradient(180deg, transparent, color-mix(in srgb, var(--cf-primary) 8%, transparent));
    }
    .cf-footer-grid {
      max-width: 1100px; margin: 0 auto;
      display: grid; gap: 1.5rem;
    }
    @media (min-width: 640px) {
      .cf-footer-grid { grid-template-columns: 1.4fr 1fr 1fr; }
    }
    .cf-footer-brand { font-family: var(--cf-font-display); font-weight: 700; font-size: 1.1rem; color: #f8fafc; }
    .cf-footer-muted { font-size: 0.85rem; color: var(--cf-muted); margin-top: 0.5rem; max-width: 28rem; }
    .cf-footer-links { list-style: none; margin: 0; padding: 0; font-size: 0.85rem; }
    .cf-footer-links li { margin-bottom: 0.4rem; }
    .cf-footer-links a { color: var(--cf-muted); }
    .cf-footer-cta-box {
      padding: 1.25rem; border-radius: 16px;
      background: linear-gradient(135deg, color-mix(in srgb, var(--cf-primary) 22%, transparent), transparent);
      border: 1px solid color-mix(in srgb, var(--cf-primary) 30%, transparent);
    }
    .cf-footer-bottom {
      max-width: 1100px; margin: 1.5rem auto 0; padding-top: 1rem;
      border-top: 1px solid rgba(255,255,255,0.06);
      font-size: 0.75rem; color: #64748b;
      display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; justify-content: space-between;
    }
    .cf-hero-img {
      width: 100%; max-width: 520px; margin: 2rem auto 0;
      border-radius: 20px; overflow: hidden;
      box-shadow: 0 24px 64px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.08);
    }
    .cf-hero-img img { width: 100%; aspect-ratio: 16/10; object-fit: cover; }
    .cf-counter { font-variant-numeric: tabular-nums; }
    .cf-with-sidebar .cf-sidebar {
      display: none; position: fixed; top: 0; left: 0; bottom: 0; z-index: 50;
      width: min(272px, 88vw); flex-direction: column; padding: 1.25rem 0;
      background: linear-gradient(180deg, color-mix(in srgb, var(--cf-bg) 95%, #000), var(--cf-bg));
      border-right: 1px solid rgba(255,255,255,0.07);
      transform: translateX(-100%);
      transition: transform 0.35s cubic-bezier(.4,0,.2,1);
      box-shadow: 12px 0 48px rgba(0,0,0,0.4);
    }
    .cf-shell.cf-nav-open .cf-sidebar { display: flex; transform: translateX(0); }
    .cf-sidebar-backdrop {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,0.55); z-index: 40;
      backdrop-filter: blur(2px);
    }
    .cf-shell.cf-nav-open .cf-sidebar-backdrop { display: block; }
    .cf-topbar {
      height: 60px; display: flex; align-items: center; gap: 0.85rem;
      padding: 0 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.07);
      background: color-mix(in srgb, var(--cf-bg) 88%, transparent);
      backdrop-filter: blur(12px);
    }
    .cf-main { padding: 1rem; min-height: calc(100vh - 60px); }
    @media (min-width: 900px) {
      .cf-menu-btn { display: none !important; }
      .cf-mobile-nav { display: none !important; }
      .cf-nav-desktop { display: flex !important; }
      .cf-with-sidebar .cf-sidebar {
        display: flex !important; transform: translateX(0) !important;
      }
      .cf-sidebar-backdrop { display: none !important; }
      .cf-with-sidebar .cf-main { margin-left: min(272px, 28vw); }
    }
    .cf-sidebar-nav {
      display: block; width: 100%; text-align: left;
      padding: 0.55rem 0.85rem; border-radius: 10px;
      color: var(--cf-muted); font-size: 0.875rem; margin-bottom: 0.15rem;
      border: none; background: transparent; cursor: pointer;
      font-family: var(--cf-font-body); transition: background 0.2s, color 0.2s;
    }
    .cf-sidebar-nav:hover {
      background: rgba(255,255,255,0.05); color: #e2e8f0;
    }
    .cf-sidebar-nav.active {
      color: #e0e7ff;
      background: color-mix(in srgb, var(--cf-primary) 18%, transparent);
    }
    .cf-app-view { display: none; animation: cfViewIn 0.35s ease; }
    .cf-app-view.active { display: block; }
    @keyframes cfViewIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .cf-header-tabs {
      display: none; gap: 0.35rem; flex-wrap: wrap;
      padding: 0 1.25rem 0.75rem;
    }
    .cf-header-tab {
      padding: 0.45rem 0.85rem; border-radius: 10px; font-size: 0.8rem; font-weight: 600;
      border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.04);
      color: var(--cf-muted); cursor: pointer; font-family: var(--cf-font-body);
    }
    .cf-header-tab.active, .cf-header-tab:hover {
      color: #f8fafc;
      background: color-mix(in srgb, var(--cf-primary) 16%, transparent);
      border-color: color-mix(in srgb, var(--cf-primary) 30%, transparent);
    }
    @media (max-width: 899px) { .cf-header-tabs { display: flex; } }
    .cf-modal-backdrop {
      display: none; position: fixed; inset: 0; z-index: 200;
      background: rgba(0,0,0,0.65); backdrop-filter: blur(6px);
      align-items: center; justify-content: center; padding: 1rem;
    }
    .cf-modal-backdrop.open { display: flex; }
    .cf-modal {
      width: 100%; max-width: 440px;
      background: var(--cf-surface);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px; padding: 1.5rem;
      box-shadow: 0 24px 80px rgba(0,0,0,0.5);
      position: relative;
    }
    .cf-modal h2 {
      margin: 0 0 0.35rem; font-size: 1.25rem; color: #f8fafc;
    }
    .cf-modal-sub { margin: 0 0 1.25rem; font-size: 0.85rem; color: var(--cf-muted); }
    .cf-modal-close {
      position: absolute; top: 1rem; right: 1rem;
      width: 36px; height: 36px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.05);
      color: #94a3b8; cursor: pointer; font-size: 1.25rem; line-height: 1;
    }
    .cf-modal-close:hover { color: #f8fafc; background: rgba(255,255,255,0.1); }
    .cf-field { margin-bottom: 0.85rem; }
    .cf-field label {
      display: block; font-size: 0.72rem; text-transform: uppercase;
      letter-spacing: 0.05em; color: var(--cf-muted); margin-bottom: 0.35rem;
    }
    .cf-field input, .cf-field textarea {
      width: 100%; padding: 0.65rem 0.8rem; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(0,0,0,0.28); color: #f1f5f9;
      font-family: var(--cf-font-body); font-size: 0.9rem;
    }
    .cf-field textarea { min-height: 110px; resize: vertical; }
    .cf-field input:focus, .cf-field textarea:focus {
      outline: none; border-color: color-mix(in srgb, var(--cf-primary) 50%, transparent);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--cf-primary) 18%, transparent);
    }
    .cf-toast {
      position: fixed; bottom: 1.25rem; left: 50%; transform: translateX(-50%) translateY(120%);
      z-index: 300; padding: 0.75rem 1.25rem; border-radius: 12px;
      background: rgba(15,23,42,0.95); border: 1px solid rgba(255,255,255,0.12);
      color: #e2e8f0; font-size: 0.875rem; max-width: min(90vw, 420px);
      text-align: center; box-shadow: 0 12px 40px rgba(0,0,0,0.4);
      transition: transform 0.35s cubic-bezier(.34,1.56,.64,1);
      pointer-events: none;
    }
    .cf-toast.show { transform: translateX(-50%) translateY(0); }
    body.cf-modal-open { overflow: hidden; }
"""


def sidebar_nav_html(
    items: tuple[tuple[str, str], ...],
    *,
    active: str | None = None,
) -> str:
    """Boutons sidebar — data-cf-nav pour changement de vue."""
    if not items:
        return ""
    first_id = items[0][0]
    current = active or first_id
    return "\n".join(
        f'<button type="button" class="cf-sidebar-nav{" active" if vid == current else ""}" '
        f'data-cf-nav="{escape_attr(vid)}" data-cf-nav-label="{escape_attr(lbl)}">'
        f"{escape_html(lbl)}</button>"
        for vid, lbl in items
    )


def header_tabs_html(
    items: tuple[tuple[str, str], ...],
    *,
    active: str | None = None,
) -> str:
    """Onglets header (templates sans sidebar)."""
    if not items:
        return ""
    first_id = items[0][0]
    current = active or first_id
    buttons = "\n".join(
        f'<button type="button" class="cf-header-tab{" active" if vid == current else ""}" '
        f'data-cf-nav="{escape_attr(vid)}" data-cf-nav-label="{escape_attr(lbl)}">'
        f"{escape_html(lbl)}</button>"
        for vid, lbl in items
    )
    return f'<div class="cf-header-tabs" role="tablist">{buttons}</div>'


def premium_contact_modal_html() -> str:
    return f"""
  <div class="cf-modal-backdrop" id="cf-contact-modal" aria-hidden="true" role="dialog" aria-labelledby="cf-contact-title">
    <div class="cf-modal" role="document">
      <button type="button" class="cf-modal-close" data-cf-action="close-modal" aria-label="Fermer">×</button>
      <h2 id="cf-contact-title">Contacter CapCore</h2>
      <p class="cf-modal-sub">Décrivez votre projet — nous vous répondons sous 24 h.</p>
      <form id="cf-contact-form" novalidate>
        <div class="cf-field">
          <label for="cf-contact-name">Nom</label>
          <input type="text" id="cf-contact-name" name="name" required autocomplete="name" placeholder="Votre nom" />
        </div>
        <div class="cf-field">
          <label for="cf-contact-email">Email</label>
          <input type="email" id="cf-contact-email" name="email" required autocomplete="email" placeholder="vous@entreprise.fr" />
        </div>
        <div class="cf-field">
          <label for="cf-contact-message">Message</label>
          <textarea id="cf-contact-message" name="message" required placeholder="Votre besoin, délais, budget…"></textarea>
        </div>
        <button type="submit" class="cf-btn cf-btn-primary" style="width:100%;">Envoyer via Gmail</button>
      </form>
    </div>
  </div>
  <div class="cf-toast" id="cf-toast" role="status" aria-live="polite"></div>"""


def user_initials(name: str, fallback: str = "CF") -> str:
    parts = [p for p in name.split() if p.strip()]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return fallback


def theme_css(template: str) -> str:
    """Variables CSS pour le type de template."""
    p = _PALETTES.get(template, _PALETTES[TEMPLATE_TASKFLOW])
    return f"""
    :root {{
      --cf-primary: {p["primary"]};
      --cf-secondary: {p["secondary"]};
      --cf-bg: {p["bg"]};
      --cf-surface: {p["surface"]};
      --cf-glow: {p["glow"]};
      --cf-font-display: {p["font_display"]};
      --cf-font-body: {p["font_body"]};
      --cf-text: #e8edf5;
      --cf-muted: #94a3b8;
    }}
    body {{
      background:
        radial-gradient(ellipse 90% 55% at 50% -15%, var(--cf-glow), transparent 55%),
        var(--cf-bg);
    }}
    .cf-btn-primary {{
      background: linear-gradient(135deg, var(--cf-primary), color-mix(in srgb, var(--cf-primary) 68%, #0f172a)) !important;
      box-shadow: 0 8px 28px var(--cf-glow) !important;
    }}
    .cf-logo {{
      background: linear-gradient(135deg, var(--cf-primary), var(--cf-secondary)) !important;
      box-shadow: 0 8px 24px var(--cf-glow) !important;
    }}
    """


def premium_fonts_link() -> str:
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com" />'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />'
        '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700'
        '&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />'
    )


def unsplash_hero_url(template: str, *, vertical: str = "") -> str:
    v = (vertical or "").lower()
    if "restaurant" in v or template == TEMPLATE_RESERVATION:
        return _UNSPLASH["restaurant"]
    if "marketing" in v:
        return _UNSPLASH["marketing"]
    if "real_estate" in v or "immobilier" in v:
        return _UNSPLASH["realestate"]
    if "artisan" in v or "plomb" in v or "électric" in v or "electric" in v:
        return _UNSPLASH["artisan"]
    if "coiff" in v or "beaut" in v or "salon" in v:
        return _UNSPLASH["beauty"]
    if "fitness" in v or "sport" in v or "gym" in v:
        return _UNSPLASH["fitness"]
    return _UNSPLASH.get(template, _UNSPLASH["landing"])


def premium_header_html(
    *,
    brand_name: str,
    brand_tag: str,
    initials: str,
    template: str,
    nav_links: tuple[tuple[str, str], ...] = (),
    cta_label: str = "Demander une démo",
    cta_action: str = "contact",
    cta_nav_target: str = "",
    show_menu: bool = True,
) -> str:
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    ini = escape_html(initials)
    cta = escape_html(cta_label)
    cta_act = escape_attr(cta_action)
    cta_nav = (
        f' data-cf-nav-target="{escape_attr(cta_nav_target)}"'
        if cta_nav_target
        else ""
    )
    links = nav_links or (
        ("#features", "Fonctionnalités"),
        ("#temoignages", "Témoignages"),
        ("#cta", "Tarifs"),
    )
    nav_desktop = "".join(
        f'<a href="{escape_attr(h)}" data-cf-action="scroll" data-cf-target="{escape_attr(h)}">'
        f"{escape_html(l)}</a>"
        for h, l in links
    )
    nav_mobile = "".join(
        f'<a href="{escape_attr(h)}" data-cf-action="scroll" data-cf-target="{escape_attr(h)}">'
        f"{escape_html(l)}</a>"
        for h, l in links
    )
    menu_btn = ""
    if show_menu:
        menu_btn = (
            '<button type="button" class="cf-menu-btn" aria-label="Menu" aria-expanded="false">'
            "<span></span><span></span><span></span></button>"
        )
    return f"""
    <header class="cf-site-header cf-reveal">
      <div class="cf-brand-block">
        {menu_btn}
        <div class="cf-logo">{ini}</div>
        <div>
          <div class="cf-brand-name">{brand}</div>
          <div class="cf-brand-tag">{tag}</div>
        </div>
      </div>
      <nav class="cf-nav-desktop" aria-label="Navigation principale">{nav_desktop}</nav>
      <div class="cf-header-actions">
        <button type="button" class="cf-btn cf-btn-primary" data-cf-action="{cta_act}"{cta_nav}>{cta}</button>
      </div>
    </header>
    <nav class="cf-mobile-nav" aria-label="Navigation mobile">{nav_mobile}</nav>"""


def premium_footer_html(*, brand_name: str, template: str = TEMPLATE_LANDING) -> str:
    brand = escape_html(brand_name)
    cta = "Parlons de votre projet avec CapCore"
    if template == TEMPLATE_CRM:
        cta = "Déployez votre CRM sur mesure avec CapCore"
    elif template == TEMPLATE_DASHBOARD:
        cta = "Construisez votre dashboard data avec CapCore"
    elif template == TEMPLATE_FACTURATION:
        cta = "Automatisez votre facturation avec CapCore"
    elif template == TEMPLATE_RESERVATION:
        cta = "Digitalisez vos réservations avec CapCore"
    elif template == TEMPLATE_TASKFLOW:
        cta = "Lancez votre workspace collaboratif avec CapCore"
    return f"""
    <footer class="cf-site-footer cf-reveal" id="cf-footer">
      <div class="cf-footer-grid">
        <div>
          <div class="cf-footer-brand">{brand}</div>
          <p class="cf-footer-muted">
            Démo interactive réalisée par CapCore — agence digitale spécialisée en produits
            sur mesure, UX premium et déploiement rapide.
          </p>
        </div>
        <div>
          <div style="font-weight:600;color:#e2e8f0;margin-bottom:0.5rem;font-size:0.85rem;">Produit</div>
          <ul class="cf-footer-links">
            <li><a href="#features">Fonctionnalités</a></li>
            <li><a href="#temoignages">Références</a></li>
            <li><a href="#cta">Tarifs</a></li>
          </ul>
        </div>
        <div class="cf-footer-cta-box">
          <div style="font-weight:700;color:#f8fafc;margin-bottom:0.35rem;font-size:0.95rem;">{escape_html(cta)}</div>
          <p style="margin:0 0 0.85rem;font-size:0.8rem;color:var(--cf-muted);">
            Réponse sous 24 h · Devis gratuit · Accompagnement de A à Z
          </p>
          <button type="button" class="cf-btn cf-btn-primary" style="width:100%;" data-cf-action="contact">
            Contacter CapCore →
          </button>
        </div>
      </div>
      <div class="cf-footer-bottom">
        <span>© 2026 CapCore · Démo {brand}</span>
        <span>Conçu avec CyberForge</span>
      </div>
    </footer>"""


def shell_nav_script(shell_id: str = "cf-shell") -> str:
    """Menu mobile — doit rester dans <script>, jamais en texte visible."""
    return f"""
  <script>
  (function() {{
    var shell = document.getElementById("{shell_id}");
    if (!shell) return;
    var btn = shell.querySelector(".cf-menu-btn");
    var backdrop = shell.querySelector(".cf-sidebar-backdrop");
    function close() {{
      shell.classList.remove("cf-nav-open");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }}
    function toggle() {{
      shell.classList.toggle("cf-nav-open");
      if (btn) btn.setAttribute("aria-expanded", shell.classList.contains("cf-nav-open") ? "true" : "false");
    }}
    if (btn) btn.addEventListener("click", toggle);
    if (backdrop) backdrop.addEventListener("click", close);
    shell.querySelectorAll(".cf-mobile-nav a").forEach(function(a) {{
      a.addEventListener("click", close);
    }});
  }})();
  </script>"""


def assert_scripts_wrapped(html: str) -> None:
    """
    Vérifie qu'aucun JS n'apparaît hors balises <script> (régression shell_nav, etc.).
  """
    import re

    stripped = re.sub(
        r"<script\b[^>]*>[\s\S]*?</script>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    markers = (
        "document.getElementById",
        "document.querySelector",
        "addEventListener",
        "localStorage",
        "(function",
    )
    for marker in markers:
        if marker in stripped:
            raise ValueError(
                f"JavaScript visible hors <script> (marqueur « {marker} » détecté)."
            )


def premium_interaction_scripts() -> str:
    """Navigation multi-vues, modal CapCore, routage CTA."""
    email = escape_attr(CAPCORE_CONTACT_EMAIL)
    return f"""
  <script>
  (function() {{
    var CF_EMAIL = "{email}";
    var NATIVE_IDS = {{
      "inv-calc": 1, "task-add-btn": 1, "settings-save": 1,
      "saas-menu-btn": 1, "cf-contact-form": 1
    }};

    function readDemoRuntime() {{
      var el = document.getElementById("cf-demo-runtime");
      if (!el || !el.textContent) return {{}};
      try {{ return JSON.parse(el.textContent); }} catch (e) {{ return {{}}; }}
    }}
    function demoTokenFromUrl() {{
      var path = window.location.pathname || "";
      var m = path.match(/\\/d\\/([^\\/]+)/);
      return m && m[1] ? decodeURIComponent(m[1]) : "";
    }}

    var RUNTIME = readDemoRuntime();
    var DEMO_TOKEN = RUNTIME.token || demoTokenFromUrl() || "";
    var PROJECT_TITLE = RUNTIME.projectTitle || document.title || "Démo";
    var DEMO_URL = RUNTIME.demoUrl || (window.location.href || "").split("#")[0].split("?")[0];
    var API_BASE = (RUNTIME.apiBase || "").replace(/\\/$/, "");

    function submitDemoContact(name, email, message) {{
      if (!DEMO_TOKEN || !API_BASE) {{
        console.error(
          "[CapCore] Contact impossible — token ou API manquant",
          {{ token: DEMO_TOKEN, apiBase: API_BASE }}
        );
        return Promise.resolve({{ ok: false, reason: "config" }});
      }}
      var url = API_BASE + "/api/demos/" + encodeURIComponent(DEMO_TOKEN) + "/interested";
      return fetch(url, {{
        method: "POST",
        mode: "cors",
        credentials: "omit",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ name: name, email: email, message: message }})
      }})
        .then(function(r) {{
          if (!r.ok) {{
            return r.text().then(function(body) {{
              console.error("[CapCore] POST interested HTTP", r.status, body);
              return {{ ok: false, status: r.status, body: body }};
            }});
          }}
          return r.json().then(function(data) {{ return {{ ok: true, data: data }}; }});
        }})
        .catch(function(err) {{
          console.error("[CapCore] POST interested réseau", err);
          return {{ ok: false, reason: "network", error: String(err) }};
        }});
    }}

    function showToast(msg) {{
      var t = document.getElementById("cf-toast");
      if (!t) return;
      t.textContent = msg;
      t.classList.add("show");
      clearTimeout(showToast._timer);
      showToast._timer = setTimeout(function() {{ t.classList.remove("show"); }}, 3200);
    }}

    function openContactModal() {{
      var modal = document.getElementById("cf-contact-modal");
      if (!modal) return;
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("cf-modal-open");
      var nameEl = document.getElementById("cf-contact-name");
      if (nameEl) setTimeout(function() {{ nameEl.focus(); }}, 120);
    }}

    function closeContactModal() {{
      var modal = document.getElementById("cf-contact-modal");
      if (!modal) return;
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("cf-modal-open");
    }}

    function showView(viewId) {{
      if (!viewId) return;
      document.querySelectorAll("[data-cf-view]").forEach(function(el) {{
        el.classList.toggle("active", el.getAttribute("data-cf-view") === viewId);
      }});
      document.querySelectorAll("[data-cf-nav]").forEach(function(btn) {{
        var on = btn.getAttribute("data-cf-nav") === viewId;
        btn.classList.toggle("active", on);
        if (on && btn.getAttribute("data-cf-nav-label")) {{
          var titleEl = document.getElementById("cf-page-title");
          if (titleEl) titleEl.textContent = btn.getAttribute("data-cf-nav-label");
        }}
      }});
      var shell = document.getElementById("cf-shell");
      if (shell) shell.classList.remove("cf-nav-open");
      document.querySelectorAll(".saas-shell.saas-nav-open").forEach(function(el) {{
        el.classList.remove("saas-nav-open");
      }});
    }}

    function scrollToTarget(sel) {{
      if (!sel) return;
      var viewFromHash = {{
        "#view-liste": "liste", "#view-creer": "creer", "#view-planning": "planning",
        "#view-stats": "stats", "#factures": "liste", "#nouvelle": "creer"
      }};
      if (viewFromHash[sel]) {{
        showView(viewFromHash[sel]);
        return;
      }}
      if (sel === "#cf-footer") {{
        var footerBtn = document.querySelector('[data-cf-action="contact"]');
        if (footerBtn) {{ openContactModal(); return; }}
      }}
      var el = document.querySelector(sel);
      if (el) el.scrollIntoView({{ behavior: "smooth", block: "start" }});
      var shell = document.getElementById("cf-shell");
      if (shell) shell.classList.remove("cf-nav-open");
    }}

    function handleAction(el) {{
      var action = el.getAttribute("data-cf-action");
      if (!action) return;
      if (action === "contact") {{ openContactModal(); return; }}
      if (action === "close-modal") {{ closeContactModal(); return; }}
      if (action === "scroll") {{
        scrollToTarget(el.getAttribute("data-cf-target"));
        return;
      }}
      if (action === "nav") {{
        showView(el.getAttribute("data-cf-nav-target") || el.getAttribute("data-cf-nav"));
        return;
      }}
      if (action === "demo") {{
        showToast(el.getAttribute("data-cf-demo-msg") ||
          "Fonctionnalité disponible dans la version complète — contactez CapCore.");
        return;
      }}
    }}

    document.addEventListener("click", function(e) {{
      var closeBackdrop = e.target.closest("#cf-contact-modal");
      if (closeBackdrop && e.target === closeBackdrop) {{
        closeContactModal();
        return;
      }}
      var actionEl = e.target.closest("[data-cf-action]");
      if (actionEl) {{
        e.preventDefault();
        handleAction(actionEl);
        return;
      }}
      var navBtn = e.target.closest("[data-cf-nav]");
      if (navBtn && !navBtn.getAttribute("data-cf-action")) {{
        e.preventDefault();
        showView(navBtn.getAttribute("data-cf-nav"));
      }}
    }});

    var contactForm = document.getElementById("cf-contact-form");
    if (contactForm) {{
      contactForm.addEventListener("submit", function(e) {{
        e.preventDefault();
        var name = (document.getElementById("cf-contact-name") || {{}}).value || "";
        var email = (document.getElementById("cf-contact-email") || {{}}).value || "";
        var message = (document.getElementById("cf-contact-message") || {{}}).value || "";
        if (!name.trim() || !email.trim() || !message.trim()) {{
          showToast("Merci de remplir tous les champs.");
          return;
        }}
        var n = name.trim();
        var em = email.trim();
        var msg = message.trim();
        var btn = contactForm.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        submitDemoContact(n, em, msg).then(function(result) {{
          if (btn) btn.disabled = false;
          closeContactModal();
          contactForm.reset();
          if (result.ok) {{
            showToast("Merci ! CapCore a bien reçu votre message — nous vous recontactons sous 48 h.");
          }} else {{
            showToast("Message non enregistré — réessayez ou écrivez à " + CF_EMAIL);
          }}
        }});
      }});
    }}

    document.addEventListener("keydown", function(e) {{
      if (e.key === "Escape") closeContactModal();
    }});

    document.querySelectorAll(".cf-btn-primary:not([data-cf-action])").forEach(function(btn) {{
      if (btn.closest("#cf-contact-form")) return;
      if (btn.id && NATIVE_IDS[btn.id]) return;
      if (btn.classList.contains("btn-add")) return;
      btn.setAttribute("data-cf-action", "contact");
    }});
    document.querySelectorAll(".cf-btn-ghost:not([data-cf-action])").forEach(function(btn) {{
      if (btn.id && NATIVE_IDS[btn.id]) return;
      btn.setAttribute("data-cf-action", "demo");
      if (!btn.getAttribute("data-cf-demo-msg")) {{
        btn.setAttribute("data-cf-demo-msg",
          "Export et téléchargements — inclus dans votre version CapCore sur mesure.");
      }}
    }});

    window.CyberForgeDemo = {{
      openContact: openContactModal,
      showView: showView,
      showToast: showToast
    }};
  }})();
  </script>"""


def premium_motion_scripts() -> str:
    """Reveal + compteurs animés (subtil, respecte prefers-reduced-motion)."""
    return """
  <script>
  (function() {
    var reduce = false;
    try { reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e) {}

    function revealNow(el) { el.classList.add("cf-in"); }

    function initReveal() {
      var nodes = Array.prototype.slice.call(document.querySelectorAll(".cf-reveal"));
      if (reduce) { nodes.forEach(revealNow); return; }
      if (!("IntersectionObserver" in window)) { nodes.forEach(revealNow); return; }
      var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) { revealNow(entry.target); io.unobserve(entry.target); }
        });
      }, { root: null, threshold: 0.12, rootMargin: "0px 0px -10% 0px" });
      nodes.forEach(function(n) { io.observe(n); });
    }

    function parseCounter(el) {
      var raw = (el.getAttribute("data-target") || el.textContent || "0").trim();
      var suffix = (el.getAttribute("data-suffix") || "").trim();
      var prefix = (el.getAttribute("data-prefix") || "").trim();
      var num = parseFloat(raw.replace(/[^0-9.,]/g, "").replace(",", ".")) || 0;
      return { num: num, suffix: suffix, prefix: prefix, decimals: (raw.split(/[.,]/)[1] || "").length };
    }

    function animateNumber(el) {
      var p = parseCounter(el);
      if (!p.num) return;
      if (reduce) {
        var fixed = p.decimals ? p.num.toFixed(p.decimals) : String(Math.round(p.num));
        el.textContent = p.prefix + fixed + p.suffix;
        return;
      }
      var dur = 900;
      var t0 = performance.now();
      function tick(now) {
        var t = Math.min(1, (now - t0) / dur);
        var v = (1 - Math.pow(1 - t, 3)) * p.num;
        var n = p.decimals ? v.toFixed(p.decimals) : Math.round(v).toLocaleString("fr-FR");
        el.textContent = p.prefix + n + p.suffix;
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }

    function initCounters() {
      var nodes = Array.prototype.slice.call(document.querySelectorAll(".cf-counter[data-target], .cf-counter[data-count]"));
      if (!nodes.length) return;
      if (reduce || !("IntersectionObserver" in window)) {
        nodes.forEach(animateNumber);
        return;
      }
      var io = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          io.unobserve(el);
          animateNumber(el);
        });
      }, { threshold: 0.35 });
      nodes.forEach(function(n) { io.observe(n); });
    }

    function initMotion() { initReveal(); initCounters(); }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initMotion);
    else initMotion();
  })();
  </script>"""


def premium_page_wrap(
    *,
    title: str,
    marker: str,
    template: str,
    extra_css: str,
    body_html: str,
    extra_scripts: str = "",
) -> str:
    """Enveloppe HTML complète pour templates marketing / app."""
    page_title = escape_html(title)
    out = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {marker} -->
  {premium_fonts_link()}
  <style>
{theme_css(template)}
{PREMIUM_BASE_CSS}
{extra_css}
  </style>
</head>
<body class="{escape_html(marker)}">
{body_html}
{premium_contact_modal_html()}
{extra_scripts}
{shell_nav_script()}
{premium_interaction_scripts()}
{premium_motion_scripts()}
</body>
</html>"""
    assert_scripts_wrapped(out)
    return out
