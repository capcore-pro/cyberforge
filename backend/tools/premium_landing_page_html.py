"""Template premium — landing page (hero, features, témoignages, CTA CapCore)."""

from __future__ import annotations

from tools.premium_base import (
    TEMPLATE_LANDING,
    escape_html,
    premium_footer_html,
    premium_header_html,
    premium_page_wrap,
    unsplash_hero_url,
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
    hero_img = unsplash_hero_url(TEMPLATE_LANDING)

    extra_css = """
    .cf-landing-hero {
      padding: 3.5rem 1.25rem 2rem;
      text-align: center;
      max-width: 1100px; margin: 0 auto;
    }
    .cf-landing-hero h1 {
      font-size: clamp(2rem, 6vw, 3.25rem);
      font-weight: 800; color: #f8fafc; margin: 0 0 1rem; line-height: 1.1;
    }
    .cf-landing-hero .cf-lead {
      max-width: 38rem; margin: 0 auto 1.75rem; color: var(--cf-muted); font-size: 1.1rem;
    }
    .cf-landing-hero .cf-trust {
      margin-top: 1.25rem; font-size: 0.82rem; color: #64748b;
    }
    .cf-landing-features {
      display: grid; grid-template-columns: 1fr; gap: 1.25rem;
      padding: 2rem 1.25rem; max-width: 1100px; margin: 0 auto;
    }
    @media (min-width: 700px) { .cf-landing-features { grid-template-columns: repeat(3, 1fr); } }
    .cf-feature-icon {
      width: 48px; height: 48px; border-radius: 14px;
      background: color-mix(in srgb, var(--cf-primary) 22%, transparent);
      color: var(--cf-secondary);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.35rem; margin-bottom: 0.85rem;
    }
    .cf-testimonials {
      padding: 1rem 1.25rem 2.5rem; max-width: 1100px; margin: 0 auto;
      display: grid; gap: 1.25rem;
    }
    @media (min-width: 700px) { .cf-testimonials { grid-template-columns: 1fr 1fr; } }
    .cf-testimonial-quote { font-style: italic; color: #cbd5e1; margin: 0 0 1rem; font-size: 1rem; line-height: 1.65; }
    .cf-testimonial-author { font-size: 0.85rem; color: var(--cf-muted); }
    .cf-testimonial-avatar {
      width: 44px; height: 44px; border-radius: 50%; object-fit: cover; margin-bottom: 0.75rem;
      border: 2px solid color-mix(in srgb, var(--cf-primary) 40%, transparent);
    }
    .cf-landing-cta {
      text-align: center; padding: 3rem 1.25rem 1rem;
      max-width: 720px; margin: 0 auto;
    }
    .cf-landing-cta h2 { margin: 0 0 0.75rem; font-size: clamp(1.5rem, 4vw, 2rem); color: #f8fafc; }
    .cf-stats-row {
      display: flex; flex-wrap: wrap; justify-content: center; gap: 2rem;
      padding: 2rem 1.25rem; max-width: 900px; margin: 0 auto;
    }
    .cf-stat-item { text-align: center; }
    .cf-stat-value {
      font-family: var(--cf-font-display); font-size: 2rem; font-weight: 800;
      color: #f8fafc;
    }
    .cf-stat-label { font-size: 0.8rem; color: var(--cf-muted); margin-top: 0.25rem; }
    """

    body = f"""
  <div class="cf-shell" id="cf-shell">
{premium_header_html(
    brand_name=brand_name,
    brand_tag=brand_tag or "Plateforme tout-en-un",
    initials=initials,
    template=TEMPLATE_LANDING,
    cta_label=hero_cta,
)}

    <section class="cf-landing-hero cf-reveal" id="cf-landing-hero">
      <h1>{page_title}</h1>
      <p class="cf-lead">{sub}</p>
      <button type="button" class="cf-btn cf-btn-primary" data-cf-action="contact">{cta}</button>
      <p class="cf-trust">Essai 14 jours · Sans carte bancaire · +2 400 équipes</p>
      <div class="cf-hero-img">
        <img src="{hero_img}" alt="Aperçu produit {brand}" loading="lazy" width="800" height="500" />
      </div>
    </section>

    <div class="cf-stats-row cf-reveal">
      <div class="cf-stat-item">
        <div class="cf-stat-value cf-counter" data-target="2400" data-suffix="+">0</div>
        <div class="cf-stat-label">Clients actifs</div>
      </div>
      <div class="cf-stat-item">
        <div class="cf-stat-value cf-counter" data-target="98" data-suffix="%">0</div>
        <div class="cf-stat-label">Satisfaction</div>
      </div>
      <div class="cf-stat-item">
        <div class="cf-stat-value cf-counter" data-target="48" data-suffix="h">0</div>
        <div class="cf-stat-label">Mise en ligne moyenne</div>
      </div>
    </div>

    <section class="cf-landing-features" id="features">
      <div class="cf-card cf-reveal">
        <div class="cf-feature-icon">⚡</div>
        <h3 style="margin:0 0 0.4rem;color:#f8fafc;">{f1}</h3>
        <p style="margin:0;color:var(--cf-muted);font-size:0.9rem;">Mise en production guidée, monitoring et SLA inclus.</p>
      </div>
      <div class="cf-card cf-reveal">
        <div class="cf-feature-icon">🔒</div>
        <h3 style="margin:0 0 0.4rem;color:#f8fafc;">{f2}</h3>
        <p style="margin:0;color:var(--cf-muted);font-size:0.9rem;">Chiffrement bout-en-bout, SSO et journaux d'audit RGPD.</p>
      </div>
      <div class="cf-card cf-reveal">
        <div class="cf-feature-icon">💬</div>
        <h3 style="margin:0 0 0.4rem;color:#f8fafc;">{f3}</h3>
        <p style="margin:0;color:var(--cf-muted);font-size:0.9rem;">Experts dédiés, onboarding personnalisé et support 7j/7.</p>
      </div>
    </section>

    <section class="cf-testimonials" id="temoignages">
      <div class="cf-card cf-reveal">
        <img class="cf-testimonial-avatar" src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=88&q=80&auto=format&fit=facearea&facepad=2" alt="" width="44" height="44" loading="lazy" />
        <p class="cf-testimonial-quote">« {t1_quote} »</p>
        <div class="cf-testimonial-author">— {t1_author}, {t1_role}</div>
      </div>
      <div class="cf-card cf-reveal">
        <img class="cf-testimonial-avatar" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=88&q=80&auto=format&fit=facearea&facepad=2" alt="" width="44" height="44" loading="lazy" />
        <p class="cf-testimonial-quote">« {t2_quote} »</p>
        <div class="cf-testimonial-author">— {t2_author}, {t2_role}</div>
      </div>
    </section>

    <section class="cf-landing-cta cf-reveal" id="cta">
      <h2>Prêt à lancer {brand} ?</h2>
      <p style="color:var(--cf-muted);margin:0 0 1.5rem;">Rejoignez les équipes qui convertissent plus vite.</p>
      <button type="button" class="cf-btn cf-btn-primary" data-cf-action="contact">{cta}</button>
    </section>

{premium_footer_html(brand_name=brand_name, template=TEMPLATE_LANDING)}
  </div>"""

    return premium_page_wrap(
        title=title,
        marker=LANDING_MARKER,
        template=TEMPLATE_LANDING,
        extra_css=extra_css,
        body_html=body,
    )
