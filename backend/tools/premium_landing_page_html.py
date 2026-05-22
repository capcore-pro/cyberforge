"""Template premium — landing page (hero, features, CTA, témoignages)."""

from __future__ import annotations

from tools.premium_base import (
    CYBERFORGE_PREVIEW_MARKER,
    PREMIUM_BASE_CSS,
    escape_attr,
    escape_html,
    shell_nav_script,
    user_initials,
)

LANDING_MARKER = "cf-premium-landing"


def build_premium_landing_html(
    *,
    title: str = "Votre produit",
    subtitle: str | None = None,
    brand_name: str = "NovaLaunch",
    brand_tag: str = "Plateforme tout-en-un",
    user_name: str = "Alex Martin",
    user_role: str = "Fondateur",
    hero_cta: str = "Démarrer gratuitement",
    features: tuple[str, ...] | list[str] | None = None,
    testimonials: list[dict[str, str]] | None = None,
) -> str:
    from tools.premium_demo_data import LANDING_FEATURES, LANDING_TESTIMONIALS

    page_title = escape_html(title)
    sub = escape_html(subtitle or "La solution moderne pour accélérer votre croissance.")
    brand = escape_html(brand_name)
    tag = escape_html(brand_tag)
    cta = escape_html(hero_cta)
    feats = tuple(features or LANDING_FEATURES)
    f1 = escape_html(feats[0] if len(feats) > 0 else "Déploiement rapide")
    f2 = escape_html(feats[1] if len(feats) > 1 else "Sécurité entreprise")
    f3 = escape_html(feats[2] if len(feats) > 2 else "Support prioritaire")
    tests = list(testimonials or LANDING_TESTIMONIALS)
    t1 = tests[0] if tests else {}
    t2 = tests[1] if len(tests) > 1 else tests[0] if tests else {}
    t1_quote = escape_html(str(t1.get("quote") or f"{brand_name} accélère votre croissance."))
    t2_quote = escape_html(str(t2.get("quote") or "Interface claire et onboarding fluide."))
    t1_author = escape_html(str(t1.get("author") or "Jean Dupont"))
    t2_author = escape_html(str(t2.get("author") or "Marie Martin"))
    t1_role = escape_html(str(t1.get("role") or "Directeur général"))
    t2_role = escape_html(str(t2.get("role") or "Directrice marketing"))
    initials = escape_html(user_initials(user_name))

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {CYBERFORGE_PREVIEW_MARKER} {LANDING_MARKER} -->
  <style>
{PREMIUM_BASE_CSS}
    .cf-landing-header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 1rem 1.25rem; border-bottom: 1px solid rgba(255,255,255,0.06);
      background: rgba(15,23,42,0.9); backdrop-filter: blur(10px);
      position: sticky; top: 0; z-index: 40;
    }}
    .cf-landing-brand {{ display: flex; align-items: center; gap: 0.75rem; }}
    .cf-landing-brand-name {{ font-weight: 700; color: #f8fafc; }}
    .cf-landing-brand-tag {{ font-size: 0.7rem; color: #64748b; }}
    .cf-landing-nav {{ display: none; gap: 1.25rem; font-size: 0.875rem; color: #94a3b8; }}
    .cf-landing-hero {{
      padding: 3rem 1.25rem 2.5rem;
      text-align: center;
      background: radial-gradient(ellipse 80% 60% at 50% -20%, rgba(99,102,241,0.35), transparent);
    }}
    .cf-landing-hero h1 {{
      font-size: clamp(1.75rem, 5vw, 2.75rem);
      font-weight: 800; color: #f8fafc; margin: 0 0 1rem;
      letter-spacing: -0.03em; line-height: 1.15;
    }}
    .cf-landing-hero p {{
      max-width: 36rem; margin: 0 auto 1.5rem; color: #94a3b8; font-size: 1.05rem;
    }}
    .cf-landing-features {{
      display: grid; grid-template-columns: 1fr; gap: 1rem;
      padding: 1rem 1.25rem 2rem; max-width: 960px; margin: 0 auto;
    }}
    @media (min-width: 640px) {{ .cf-landing-features {{ grid-template-columns: repeat(3, 1fr); }} }}
    .cf-feature-icon {{
      width: 44px; height: 44px; border-radius: 12px;
      background: rgba(99,102,241,0.2); color: #a5b4fc;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.25rem; margin-bottom: 0.75rem;
    }}
    .cf-testimonials {{
      padding: 2rem 1.25rem; max-width: 960px; margin: 0 auto;
      display: grid; gap: 1rem;
    }}
    @media (min-width: 700px) {{ .cf-testimonials {{ grid-template-columns: 1fr 1fr; }} }}
    .cf-testimonial-quote {{ font-style: italic; color: #cbd5e1; margin: 0 0 0.75rem; }}
    .cf-testimonial-author {{ font-size: 0.8rem; color: #64748b; }}
    .cf-landing-cta {{
      text-align: center; padding: 2.5rem 1.25rem 3rem;
      background: linear-gradient(180deg, transparent, rgba(99,102,241,0.12));
    }}
    @media (min-width: 768px) {{ .cf-landing-nav {{ display: flex; }} }}
  </style>
</head>
<body>
  <div class="cf-shell" id="cf-shell">
    <header class="cf-landing-header">
      <div class="cf-landing-brand">
        <div class="cf-logo">{initials}</div>
        <div>
          <div class="cf-landing-brand-name">{brand}</div>
          <div class="cf-landing-brand-tag">{tag}</div>
        </div>
      </div>
      <nav class="cf-landing-nav" aria-label="Navigation">
        <a href="#features">Fonctionnalités</a>
        <a href="#temoignages">Témoignages</a>
        <a href="#cta">Tarifs</a>
      </nav>
      <button type="button" class="cf-btn cf-btn-primary">{cta}</button>
    </header>

    <section class="cf-landing-hero" id="cf-landing-hero">
      <h1>{page_title}</h1>
      <p>{sub}</p>
      <button type="button" class="cf-btn cf-btn-primary">{cta}</button>
      <p style="margin-top:1rem;font-size:0.8rem;color:#64748b;">Essai 14 jours · Sans carte bancaire</p>
    </section>

    <section class="cf-landing-features" id="features">
      <div class="cf-card">
        <div class="cf-feature-icon">⚡</div>
        <h3 style="margin:0 0 0.35rem;color:#f8fafc;">{f1}</h3>
        <p style="margin:0;color:#94a3b8;font-size:0.875rem;">Mise en production guidée et monitoring inclus.</p>
      </div>
      <div class="cf-card">
        <div class="cf-feature-icon">🔒</div>
        <h3 style="margin:0 0 0.35rem;color:#f8fafc;">{f2}</h3>
        <p style="margin:0;color:#94a3b8;font-size:0.875rem;">Chiffrement, SSO et journaux d'audit conformes RGPD.</p>
      </div>
      <div class="cf-card">
        <div class="cf-feature-icon">💬</div>
        <h3 style="margin:0 0 0.35rem;color:#f8fafc;">{f3}</h3>
        <p style="margin:0;color:#94a3b8;font-size:0.875rem;">Experts dédiés et base de connaissances enrichie.</p>
      </div>
    </section>

    <section class="cf-testimonials" id="temoignages">
      <div class="cf-card">
        <p class="cf-testimonial-quote">« {t1_quote} »</p>
        <div class="cf-testimonial-author">— {t1_author}, {t1_role}</div>
      </div>
      <div class="cf-card">
        <p class="cf-testimonial-quote">« {t2_quote} »</p>
        <div class="cf-testimonial-author">— {t2_author}, {t2_role}</div>
      </div>
    </section>

    <section class="cf-landing-cta" id="cta">
      <h2 style="margin:0 0 0.75rem;color:#f8fafc;">Prêt à lancer {brand} ?</h2>
      <p style="color:#94a3b8;margin:0 0 1.25rem;">Rejoignez plus de 2 400 équipes satisfaites.</p>
      <button type="button" class="cf-btn cf-btn-primary">{cta}</button>
    </section>
  </div>
  <script>{shell_nav_script()}</script>
</body>
</html>"""
