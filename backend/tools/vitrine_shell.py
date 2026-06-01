"""
Shell visuel premium pour vitrines HTML (navbar, hero plein écran, sections).
"""

from __future__ import annotations

import html as html_lib
import re

from tools.client_content_profile import (
    ClientContentProfile,
    format_client_h1,
    format_client_page_title,
    format_client_tagline,
)

_HERO_IMAGES: dict[str, str] = {
    "boulangerie": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1920&q=80",
    "restauration": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1920&q=80",
    "coiffure": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80",
    "immobilier": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=1920&q=80",
    "default": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
}

_PREMIUM_CSS = """
:root {
  --cf-brand: #5c3a21;
  --cf-brand-light: #7a4f30;
  --cf-cream: #fcf7f0;
  --cf-text: #2e2418;
  --cf-muted: #6b5344;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--cf-cream);
  color: var(--cf-text);
  line-height: 1.55;
}
.cf-vitrine-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 1000;
  background: rgba(46, 36, 24, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 0.75rem 0;
}
.cf-vitrine-nav .cf-nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.cf-vitrine-logo {
  font-weight: 700;
  font-size: 1.25rem;
  color: #fae1c3;
  letter-spacing: 0.02em;
}
.cf-vitrine-navlinks {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}
.cf-vitrine-navlinks a {
  color: #f5e6d3;
  text-decoration: none;
  font-size: 0.95rem;
  font-weight: 500;
}
.cf-vitrine-navlinks a:hover { color: #fff; }
.cf-vitrine-hero {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 6rem 1.5rem 4rem;
  margin-top: 3.5rem;
  background-size: cover;
  background-position: center;
  color: #fff;
}
.cf-vitrine-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(20,12,8,0.55) 0%, rgba(20,12,8,0.75) 100%);
}
.cf-vitrine-hero .cf-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 820px;
}
.cf-vitrine-hero h1 {
  font-size: clamp(2rem, 5vw, 3.25rem);
  font-weight: 800;
  margin-bottom: 0.75rem;
  text-shadow: 0 2px 24px rgba(0,0,0,0.35);
}
.cf-vitrine-hero .cf-hero-tagline {
  font-size: 1.2rem;
  margin-bottom: 1.75rem;
  opacity: 0.95;
}
.cf-vitrine-hero .cf-hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}
.cf-btn-primary {
  display: inline-block;
  background: var(--cf-brand);
  color: #fff;
  padding: 0.85rem 1.75rem;
  border-radius: 999px;
  font-weight: 600;
  text-decoration: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
}
.cf-btn-primary:hover { background: var(--cf-brand-light); }
.cf-btn-ghost {
  display: inline-block;
  border: 2px solid rgba(255,255,255,0.85);
  color: #fff;
  padding: 0.8rem 1.6rem;
  border-radius: 999px;
  font-weight: 600;
  text-decoration: none;
}
.cf-vitrine-section {
  padding: 4rem 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}
.cf-vitrine-section h2 {
  font-size: 2rem;
  margin-bottom: 1.5rem;
  color: var(--cf-brand);
}
.cf-vitrine-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
}
.cf-vitrine-card {
  background: #fff;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 12px 32px rgba(92,58,33,0.1);
}
.cf-vitrine-footer {
  background: var(--cf-brand);
  color: #f5e6d3;
  text-align: center;
  padding: 2rem 1rem;
  font-size: 0.9rem;
}
section.cf-client-hero,
section.cf-client-keywords,
section.cf-client-sector,
p.cf-client-city { display: none !important; }
@media (max-width: 640px) {
  .cf-vitrine-hero { min-height: 75vh; padding-top: 5rem; }
}
"""


def _hero_image_for_profile(profile: ClientContentProfile, prompt: str = "") -> str:
    blob = " ".join(
        [profile.sector, profile.city, " ".join(profile.keywords[:6]), prompt]
    ).lower()
    for key in ("boulangerie", "boulanger", "pâtiss", "patiss", "restaurant", "coiffure", "immobilier"):
        if key in blob:
            if "boulanger" in key or "pâtiss" in key or "patiss" in key:
                return _HERO_IMAGES["boulangerie"]
            if "restaurant" in key:
                return _HERO_IMAGES["restauration"]
            if "coiffure" in key:
                return _HERO_IMAGES["coiffure"]
            if "immobilier" in key:
                return _HERO_IMAGES["immobilier"]
    return _HERO_IMAGES["default"]


def _sanitize_html_body(html: str) -> str:
    """Retire fences markdown, documents HTML imbriqués et blocs auto-injectés."""
    from tools.html_markdown import strip_markdown_code_fences

    out = strip_markdown_code_fences(html or "")
    if out.lower().count("<!doctype") > 1 or out.lower().count("<html") > 1:
        matches = list(re.finditer(r"<!DOCTYPE html>[\s\S]*?</html>", out, re.I))
        if matches:
            out = matches[-1].group(0)
    out = re.sub(
        r'<section[^>]+class=["\'][^"\']*cf-client-hero[^"\']*["\'][^>]*>[\s\S]*?</section>',
        "",
        out,
        flags=re.I,
    )
    out = re.sub(
        r'<section[^>]+class=["\'][^"\']*cf-client-keywords[^"\']*["\'][^>]*>[\s\S]*?</section>',
        "",
        out,
        flags=re.I,
    )
    return out


def apply_vitrine_premium_shell(
    html: str,
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
) -> str:
    """Applique titre propre, hero plein écran, navbar fixe et styles premium."""
    cleaned = _sanitize_html_body(html)
    page_title = format_client_page_title(profile, user_prompt=user_prompt)
    h1_text = format_client_h1(profile, user_prompt=user_prompt)
    tagline = format_client_tagline(profile, user_prompt=user_prompt)
    brand = html_lib.escape(profile.display_name or h1_text)
    title_esc = html_lib.escape(page_title)
    h1_esc = html_lib.escape(h1_text)
    tag_esc = html_lib.escape(tagline)
    hero_img = _hero_image_for_profile(profile, user_prompt)

    body_inner = cleaned
    head_extra = ""
    if re.search(r"<html", cleaned, re.I):
        head_m = re.search(r"<head[^>]*>([\s\S]*?)</head>", cleaned, re.I)
        if head_m:
            head_extra = head_m.group(1)
        body_m = re.search(r"<body[^>]*>([\s\S]*?)</body>", cleaned, re.I)
        if body_m:
            body_inner = body_m.group(1)

    body_inner = re.sub(r"<header[^>]*>[\s\S]*?</header>", "", body_inner, count=1, flags=re.I)
    body_inner = re.sub(
        r'<section[^>]+id=["\']hero["\'][^>]*>[\s\S]*?</section>',
        "",
        body_inner,
        count=1,
        flags=re.I,
    )

    nav = f"""
<header class="cf-vitrine-nav" role="banner">
  <div class="cf-nav-inner">
    <span class="cf-vitrine-logo">{brand}</span>
    <nav class="cf-vitrine-navlinks" aria-label="Navigation">
      <a href="#hero" data-cf-action="scroll" data-cf-target="#hero">Accueil</a>
      <a href="#services" data-cf-action="scroll" data-cf-target="#services">Services</a>
      <a href="#about" data-cf-action="scroll" data-cf-target="#about">À propos</a>
      <a href="#contact" data-cf-action="scroll" data-cf-target="#contact">Contact</a>
    </nav>
  </div>
</header>
"""

    hero = f"""
<section id="hero" class="cf-vitrine-hero" style="background-image:url('{hero_img}')">
  <div class="cf-hero-inner">
    <h1>{h1_esc}</h1>
    <p class="cf-hero-tagline">{tag_esc}</p>
    <div class="cf-hero-actions">
      <a class="cf-btn-primary" href="#contact" data-cf-action="scroll" data-cf-target="#contact">Nous contacter</a>
      <a class="cf-btn-ghost" href="#services" data-cf-action="scroll" data-cf-target="#services">Nos services</a>
    </div>
  </div>
</section>
"""

    if 'id="services"' not in body_inner.lower():
        kw = profile.keywords[:3]
        cards = ""
        labels = kw or ["Prestation 1", "Prestation 2", "Prestation 3"]
        for label in labels[:3]:
            le = html_lib.escape(str(label))
            cards += f'<article class="cf-vitrine-card"><h3>{le}</h3><p>Découvrez notre expertise {le.lower()} chez {brand}.</p></article>'
        body_inner += f"""
<section id="services" class="cf-vitrine-section">
  <h2>Nos services</h2>
  <div class="cf-vitrine-cards">{cards}</div>
</section>
"""

    if 'id="about"' not in body_inner.lower():
        body_inner += f"""
<section id="about" class="cf-vitrine-section">
  <h2>À propos</h2>
  <p>{brand} vous accueille à {html_lib.escape(profile.city or "votre ville")} pour un service {html_lib.escape(profile.sector_label_for(user_prompt) or "de qualité")}.</p>
</section>
"""

    footer = f'<footer class="cf-vitrine-footer"><p>© {brand} — {html_lib.escape(profile.city or "")}</p></footer>'

    if not re.search(r"charset\s*=", head_extra, re.I):
        head_extra = '<meta charset="UTF-8" />\n<meta name="viewport" content="width=device-width, initial-scale=1" />\n' + head_extra

    head_extra = re.sub(r"<title[^>]*>[^<]*</title>", f"<title>{title_esc}</title>", head_extra, count=1, flags=re.I)
    if "<title>" not in head_extra.lower():
        head_extra = f"<title>{title_esc}</title>\n" + head_extra

    if "cf-vitrine-premium" not in head_extra:
        head_extra += f'<style id="cf-vitrine-premium">{_PREMIUM_CSS}</style>'

    doc = f"""<!DOCTYPE html>
<html lang="fr">
<head>
{head_extra.strip()}
</head>
<body>
{nav}
{hero}
{body_inner.strip()}
{footer}
</body>
</html>
"""
    return doc
