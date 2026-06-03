"""
Profil contenu client — injection littérale dans les prompts et le HTML vitrine.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.research_agent import ResearchBrief

CLIENT_LITERAL_ISSUE_CODES = frozenset(
    {
        "missing_client_name",
        "missing_sector",
        "missing_city",
        "missing_keyword",
        "missing_h1",
        "h1_not_client",
    }
)

_PROMPT_LIKE_RE = re.compile(
    r"(?i)\b(vitrine|si tu es|créer un|générer un|je veux|prompt|"
    r"cette vitrine|site web pour|description du|lorem|loi\s+visuelle)\b"
)
_QUOTED_NAME_RE = re.compile(
    r"[«\"']([^»\"']{2,40})[»\"']|"
    r"\b(?:boulangerie|restaurant|salon|cabinet|agence|studio)\s+"
    r"([A-ZÀ-ÖÙ-Ý][\w''\-]{2,30})",
    re.UNICODE | re.IGNORECASE,
)
_LOGO_NAME_RE = re.compile(
    r'class=["\'][^"\']*logo[^"\']*["\'][^>]*>\s*(?:[^\w<]*)([A-ZÀ-ÖÙ-Ý][\w''\-\s]{2,40})',
    re.I,
)

_GENERIC_BRAND_RE = re.compile(
    r"\b(acme|example\s+corp|entreprise\s+xyz|votre\s+entreprise|"
    r"company\s+name|brand\s+name|mon\s+entreprise|welcome\s+to)\b",
    re.IGNORECASE,
)

# Mots du prompt — jamais utilisés comme nom de marque.
_PROMPT_KEYWORD_NAMES: frozenset[str] = frozenset(
    {
        "vitrine",
        "site",
        "web",
        "artisanale",
        "artisanal",
        "artisan",
        "boulangerie",
        "restaurant",
        "restauration",
        "pâtisserie",
        "patisserie",
        "commerce",
        "local",
        "locale",
        "professionnel",
        "professionnelle",
        "entreprise",
        "activité",
        "activite",
        "notre",
        "entreprise",
    }
)

_BUSINESS_NAME_PREFIX_RE = re.compile(
    r"^(?:Le|La|Les|L['\u2019]|Aux|Chez|Boulangerie|Restaurant|Salon|"
    r"Cabinet|Studio|Agence|Fournil|Atelier|Maison)\b",
    re.IGNORECASE,
)

# Identités démo / artefacts pipeline — jamais injectées comme nom client.
_BLOCKED_BRAND_EXACT: frozenset[str] = frozenset(
    {
        "loi visuelle",
        "loivisuelle",
        "institut de beauté",
        "institut de beaute",
        "sophie",
        "camille",
        "léa",
        "lea",
    }
)

_BLOCKED_BRAND_SUBSTRINGS: tuple[str, ...] = (
    "loi visuelle",
    "loivisuelle",
    "contact@loivisuelle",
)

_DEMO_FIRST_NAMES_RE = re.compile(
    r"^(?:sophie|camille|léa|lea)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClientContentProfile:
    company_name: str = ""
    sector: str = ""
    city: str = ""
    keywords: list[str] = field(default_factory=list)

    @property
    def has_identity(self) -> bool:
        return bool(self.company_name.strip() or self.sector.strip())

    @property
    def display_name(self) -> str:
        return sanitize_brand_name(self.company_name)

    def sector_label_for(self, user_prompt: str = "") -> str:
        return humanize_sector_label(self.sector, self.keywords, user_prompt=user_prompt)


def is_blocked_demo_identity(name: str) -> bool:
    """True si le texte est une identité démo interdite (nom, e-mail, marque figée)."""
    n = (name or "").strip()
    if not n:
        return False
    low = n.lower()
    if low in _BLOCKED_BRAND_EXACT:
        return True
    if _DEMO_FIRST_NAMES_RE.match(low):
        return True
    return any(sub in low for sub in _BLOCKED_BRAND_SUBSTRINGS)


def safe_contact_email_domain_slug(brand: str) -> str:
    """Domaine e-mail générique — évite loivisuelle.fr et prénoms démo."""
    if is_blocked_demo_identity(brand):
        return "entreprise"
    slug = re.sub(r"[^a-z0-9]+", "", (brand or "").lower())
    if not slug or "loivisuelle" in slug or _DEMO_FIRST_NAMES_RE.match(slug):
        return "entreprise"
    return slug[:24]


def _looks_like_prompt_fragment(text: str) -> bool:
    s = (text or "").strip()
    if len(s) > 52:
        return True
    if "…" in s or "..." in s:
        return True
    if s.count(".") >= 2 or s.count("?") >= 1:
        return True
    return bool(_PROMPT_LIKE_RE.search(s))


def is_plausible_business_name(
    name: str,
    *,
    city: str = "",
    user_prompt: str = "",
) -> bool:
    """True si le nom ressemble à une enseigne (pas un mot-clé du brief)."""
    n = (name or "").strip()
    if len(n) < 3 or n == "Notre entreprise":
        return False
    low = n.lower()
    if low in _PROMPT_KEYWORD_NAMES:
        return False
    if _GENERIC_BRAND_RE.search(n):
        return False
    if _looks_like_prompt_fragment(n):
        return False
    if is_blocked_demo_identity(n):
        return False
    if "loi visuelle" in low or low in ("loi", "visuelle"):
        return False
    city_clean = sanitize_city(city).lower()
    if city_clean and low == city_clean:
        return False
    words = n.split()
    if len(words) == 1 and words[0].lower() in _PROMPT_KEYWORD_NAMES:
        return False
    if len(words) >= 2:
        return True
    if _BUSINESS_NAME_PREFIX_RE.match(n):
        return True
    # Mot unique capitalisé type « Dupont » (nom propre court)
    if len(words) == 1 and words[0][0].isupper() and len(words[0]) >= 4:
        if words[0].lower() not in _PROMPT_KEYWORD_NAMES:
            return True
    return False


def generate_fictional_business_name(
    *,
    sector: str = "",
    city: str = "",
    user_prompt: str = "",
) -> str:
    """Nom d'enseigne crédible quand le prompt ne cite pas le client."""
    city_label = sanitize_city(city) or "France"
    blob = f"{sector} {user_prompt}".lower()

    if any(x in blob for x in ("boulanger", "pâtiss", "patiss", "four", "pain")):
        variants = (
            f"Le Fournil de {city_label}",
            f"Boulangerie du Vieux-Marché",
            f"Aux Délices de {city_label}",
            f"La Mie de {city_label}",
            f"Boulangerie {city_label}",
        )
    elif any(x in blob for x in ("restaurant", "restauration", "brasserie", "bistrot")):
        variants = (
            f"La Table de {city_label}",
            f"Restaurant Le Jardin",
            f"Chez Auguste — {city_label}",
            f"Brasserie du Centre",
        )
    elif any(x in blob for x in ("coiff", "salon", "beauté", "beaute")):
        variants = (
            f"Salon Élégance {city_label}",
            f"Coiffure & Style {city_label}",
            f"L'Atelier Beauté",
        )
    elif any(x in blob for x in ("plomb", "électric", "electric", "artisan", "btp")):
        variants = (
            f"Artisan Pro {city_label}",
            f"Les Compagnons de {city_label}",
            f"Atelier {city_label}",
        )
    else:
        sector_h = humanize_sector_label(sector, user_prompt=user_prompt)
        variants = (
            f"{sector_h} {city_label}",
            f"Les Affaires de {city_label}",
            f"Maison {sector_h} — {city_label}",
        )

    seed = sum(ord(c) for c in f"{city_label}|{sector}|{user_prompt[:80]}")
    return variants[seed % len(variants)]


def resolve_client_business_name(
    raw_name: str,
    *,
    sector: str = "",
    city: str = "",
    user_prompt: str = "",
) -> str:
    """Sanitize puis nom fictif sectoriel si le prompt n'a pas de vraie enseigne."""
    candidate = sanitize_brand_name(raw_name, user_prompt=user_prompt)
    if is_plausible_business_name(
        candidate, city=city, user_prompt=user_prompt
    ):
        return candidate
    return generate_fictional_business_name(
        sector=sector,
        city=city,
        user_prompt=user_prompt,
    )


def sanitize_brand_name(raw: str, *, user_prompt: str = "", html: str = "") -> str:
    """Nom court de marque — jamais le prompt complet."""
    s = (raw or "").strip()
    if is_blocked_demo_identity(s):
        return ""
    if (
        s
        and not _looks_like_prompt_fragment(s)
        and len(s) <= 48
        and is_plausible_business_name(s, user_prompt=user_prompt)
    ):
        return s

    for match in _LOGO_NAME_RE.finditer(html or ""):
        candidate = re.sub(r"^[\W_]+", "", (match.group(1) or "").strip())
        if candidate and not _looks_like_prompt_fragment(candidate):
            return candidate[:48]

    prompt = user_prompt or ""
    for match in _QUOTED_NAME_RE.finditer(prompt):
        for group in match.groups():
            if group and not _looks_like_prompt_fragment(group):
                candidate = group.strip()[:48]
                if is_plausible_business_name(candidate, user_prompt=prompt):
                    return candidate

    m = re.search(
        r"\b(?:pour|chez|de)\s+((?:Aux|Le|La|Les)\s+)?([A-ZÀ-ÖÙ-Ý][\w''\-]+(?:\s+[A-ZÀ-ÖÙ-Ý][\w''\-]+){0,2})",
        prompt,
        re.I,
    )
    if m:
        prefix = (m.group(1) or "").strip()
        core = (m.group(2) or "").strip()
        name = f"{prefix} {core}".strip() if prefix else core
        if name and is_plausible_business_name(name, user_prompt=prompt):
            return name[:48]

    m = re.search(
        r"\b((?:Aux|Le|La|Les|Chez|Boulangerie|Restaurant|Salon)\s+)"
        r"([A-ZÀ-ÖÙ-Ý][\w''\-]+(?:\s+[A-ZÀ-ÖÙ-Ý][\w''\-]+){0,3})",
        prompt,
    )
    if m:
        name = f"{m.group(1).strip()} {m.group(2).strip()}".strip()
        if is_plausible_business_name(name, user_prompt=prompt):
            return name[:48]

    if s and len(s) <= 48:
        cut = s.split(".")[0].split("?")[0].strip()
        if cut and is_plausible_business_name(cut, user_prompt=prompt):
            return cut[:48]
    return ""


def sanitize_city(raw: str) -> str:
    c = (raw or "").strip()
    if not c:
        return ""
    parts = c.split()
    if len(parts) >= 2 and parts[-1].lower() in ("le", "la", "les", "de", "du"):
        return " ".join(parts[:-1])[:40]
    return parts[0][:40] if parts else c[:40]


def humanize_sector_label(
    sector: str,
    keywords: list[str] | None = None,
    *,
    user_prompt: str = "",
) -> str:
    blob = f"{sector} {' '.join(keywords or [])} {user_prompt}".lower()
    if any(x in blob for x in ("boulanger", "pâtiss", "patiss", "four", "pain")):
        return "Boulangerie"
    if any(x in blob for x in ("restaurant", "restauration", "brasserie")):
        return "Restauration"
    if "coiff" in blob:
        return "Coiffure"
    if any(
        x in blob
        for x in ("beauté", "beaute", "spa", "esthétique", "esthetique", "institut")
    ):
        return "Beauté & bien-être"
    if "immobilier" in blob:
        return "Immobilier"
    s = (sector or "").strip()
    if s.lower() in ("commerce", "activité locale", "services"):
        return "Commerce"
    return s.capitalize() if s else "Services"


def format_client_page_title(
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
    html: str = "",
) -> str:
    name = sanitize_brand_name(profile.company_name, user_prompt=user_prompt, html=html)
    sector = humanize_sector_label(
        profile.sector, profile.keywords, user_prompt=user_prompt
    )
    city = sanitize_city(profile.city)
    if city and sector:
        return f"{name} — {sector} {city}"[:72]
    if sector:
        return f"{name} — {sector}"[:72]
    return name[:72]


def format_client_h1(
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
    html: str = "",
) -> str:
    return sanitize_brand_name(profile.company_name, user_prompt=user_prompt, html=html)


def format_client_tagline(
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
    html: str = "",
) -> str:
    name = sanitize_brand_name(profile.company_name, user_prompt=user_prompt, html=html)
    sector = humanize_sector_label(
        profile.sector, profile.keywords, user_prompt=user_prompt
    )
    city = sanitize_city(profile.city)
    if sector and city:
        return f"{sector} artisanale — {city}"
    if sector:
        return f"{sector} — {name}"
    return f"Bienvenue chez {name}"


def _coerce_research_brief(
    research_brief: Any,
) -> Any | None:
    from agents.research_agent import ResearchBrief

    if research_brief is None:
        return None
    if isinstance(research_brief, ResearchBrief):
        return research_brief
    if isinstance(research_brief, dict):
        try:
            return ResearchBrief.model_validate(research_brief)
        except Exception:
            return ResearchBrief(
                secteur=str(research_brief.get("secteur") or ""),
                nom_entreprise=str(research_brief.get("nom_entreprise") or ""),
                ville=str(research_brief.get("ville") or ""),
                type_projet=str(research_brief.get("type_projet") or ""),
                mots_cles=list(research_brief.get("mots_cles") or []),
                tendances=list(research_brief.get("tendances") or []),
                concurrents=list(research_brief.get("concurrents") or []),
                contenu_suggere=list(research_brief.get("contenu_suggere") or []),
                exemples_sites=list(research_brief.get("exemples_sites") or []),
                skipped=bool(research_brief.get("skipped")),
                skip_reason=research_brief.get("skip_reason"),
            )
    return None


def log_client_content_context(
    profile: ClientContentProfile,
    *,
    prefix: str = "BuilderAI",
) -> None:
    import logging

    log = logging.getLogger(__name__)
    log.info(
        "[%s] contexte client | nom=%r | secteur=%r | ville=%r | mots_cles=%s",
        prefix,
        profile.company_name or "(vide)",
        profile.sector or "(vide)",
        profile.city or "(vide)",
        profile.keywords[:12] if profile.keywords else [],
    )


def build_client_content_profile(
    *,
    user_prompt: str = "",
    research_brief: Any | None = None,
    plan: Any | None = None,
) -> ClientContentProfile:
    from agents.research_agent import extract_research_context

    name = ""
    sector = ""
    city = ""
    keywords: list[str] = []

    brief = _coerce_research_brief(research_brief)
    if brief is not None:
        name = (brief.nom_entreprise or "").strip()
        if is_blocked_demo_identity(name):
            name = ""
        sector = (brief.secteur or "").strip()
        city = (brief.ville or "").strip()
        keywords = [str(k).strip() for k in (brief.mots_cles or []) if str(k).strip()]

    ctx = extract_research_context(user_prompt, plan=plan)
    if not name:
        name = (ctx.get("nom_entreprise") or "").strip()
        if is_blocked_demo_identity(name):
            name = ""
    if not sector:
        sector = (ctx.get("secteur") or "").strip()
    if plan and getattr(plan, "secteur", None):
        sector = (plan.secteur or sector).strip()

    city = sanitize_city(city)
    if not sector and ctx.get("secteur"):
        sector = (ctx.get("secteur") or "").strip()
    name = resolve_client_business_name(
        name,
        sector=sector,
        city=city,
        user_prompt=user_prompt,
    )

    return ClientContentProfile(
        company_name=name,
        sector=sector,
        city=city,
        keywords=keywords[:12],
    )


def format_literal_client_directive(
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
) -> str:
    if not profile.has_identity:
        return ""

    kw_line = ", ".join(profile.keywords) if profile.keywords else "(aucun)"
    name = profile.display_name or "—"
    sector = profile.sector_label_for(user_prompt) or "activité locale"
    city = profile.city or "France"

    return f"""
## IDENTITÉ CLIENT — À REPRODUIRE LITTÉRALEMENT DANS LE HTML
Ces chaînes doivent apparaître telles quelles (orthographe exacte) dans le document :
- Nom entreprise : {name}
- Secteur : {sector}
- Ville : {city}
- Mots-clés SEO : {kw_line}

OBLIGATOIRE dans le HTML final (texte visible, orthographe exacte) :
1. <title> : doit contenir littéralement « {name} »
2. <h1> principal : doit contenir littéralement « {name} » (pas un synonyme)
3. Corps <body> : au moins 3 mots-clés SEO parmi [{kw_line}] intégrés dans des paragraphes ou listes
4. <meta name="description"> avec « {name} », « {sector} » et « {city} »
5. Au moins 2 sections mentionnant le métier ({sector}) et la zone ({city})
6. Au moins 1 bouton CTA avec « {name} » ou « {city} »
7. Footer ou contact avec le nom « {name} » (le nom doit apparaître au moins 2 fois au total dans le document)

INTERDIT : tout autre nom de marque, texte générique SaaS, lorem ipsum, « Votre texte ici », slogans inventés
qui ne citent pas « {name} ».
""".strip() + "\n\n"


def validate_client_literals(
    html: str,
    profile: ClientContentProfile,
) -> list[tuple[str, str]]:
    brand = profile.display_name
    if not brand or brand == "Notre entreprise":
        return []

    issues: list[tuple[str, str]] = []
    body = html or ""
    low = body.lower()
    name = brand.strip()
    name_low = name.lower()

    if name_low not in low:
        issues.append(
            (
                "missing_client_name",
                f"Le nom client « {name} » doit apparaître dans le HTML.",
            )
        )
    elif low.count(name_low) < 2:
        issues.append(
            (
                "missing_client_name",
                f"Le nom « {name} » doit apparaître au moins 2 fois dans le HTML.",
            )
        )

    if profile.sector and profile.sector.lower() not in low:
        issues.append(
            (
                "missing_sector",
                f"Le secteur « {profile.sector} » doit apparaître dans le HTML.",
            )
        )

    if profile.city and profile.city.lower() not in low:
        issues.append(
            (
                "missing_city",
                f"La ville « {profile.city} » doit apparaître dans le HTML.",
            )
        )

    required_kw = [k for k in profile.keywords if len(k.strip()) >= 3][:3]
    missing_kw = [k for k in required_kw if k.lower() not in low]
    if required_kw and missing_kw:
        issues.append(
            (
                "missing_keyword",
                f"Mots-clés manquants dans le HTML : {', '.join(missing_kw)}.",
            )
        )

    if _GENERIC_BRAND_RE.search(body) and name_low not in low:
        issues.append(
            (
                "generic_brand",
                "Texte générique détecté sans le nom du client.",
            )
        )

    if re.search(r"<h1\b[^>]*>[^<]*</h1>", body, re.I):
        h1_match = re.search(r"<h1\b[^>]*>([^<]*)</h1>", body, re.I)
        if h1_match and name_low not in (h1_match.group(1) or "").lower():
            issues.append(
                (
                    "h1_not_client",
                    f"Le <h1> doit contenir le nom « {name} ».",
                )
            )
    else:
        issues.append(
            (
                "missing_h1",
                f"Un <h1> contenant « {name} » est requis.",
            )
        )

    return issues


def repair_client_literals_in_html(
    html: str,
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
) -> str:
    """
    Post-traitement déterministe : injecte nom, secteur, ville, mots-clés et h1
    sans régénération LLM (utilisé par BugHunterAI / limite AutoFix).
    """
    if not profile.company_name:
        return html
    out = enforce_client_literals_in_html(html, profile, user_prompt=user_prompt)
    if "<html" not in out.lower():
        return out

    name = html_lib.escape(profile.display_name)
    sector_txt = html_lib.escape(profile.sector or "")
    city_txt = html_lib.escape(profile.city or "")
    low = out.lower()
    name_low = profile.display_name.lower()

    if profile.sector and profile.sector.lower() not in low:
        block = (
            f'<section id="about" class="cf-client-sector">'
            f"<h2>Notre métier</h2>"
            f"<p>{name} est spécialisé en {sector_txt}.</p>"
            f"</section>\n"
        )
        out = _inject_before_body_end(out, block)

    if profile.city and profile.city.lower() not in low:
        block = (
            f'<p class="cf-client-city">Basé à {city_txt}, {name} vous accompagne localement.</p>\n'
        )
        out = _inject_before_body_end(out, block)

    required_kw = [k for k in profile.keywords if len(k.strip()) >= 3][:3]
    missing_kw = [k for k in required_kw if k.lower() not in out.lower()]
    if missing_kw:
        items = "".join(f"<li>{html_lib.escape(k)}</li>" for k in missing_kw)
        block = (
            f'<section id="services" class="cf-client-keywords">'
            f"<h2>Expertise {name}</h2><ul>{items}</ul>"
            f"</section>\n"
        )
        out = _inject_before_body_end(out, block)

    if out.lower().count(name_low) < 2:
        footer = (
            f'<footer class="cf-client-footer">'
            f"<p>© {name} — {sector_txt or 'services'} "
            f"{f'· {city_txt}' if city_txt else ''}</p>"
            f"</footer>\n"
        )
        out = _inject_before_body_end(out, footer)

    h1_match = re.search(r"(<h1\b[^>]*>)([^<]*)(</h1>)", out, re.I)
    if h1_match and name_low not in (h1_match.group(2) or "").lower():
        out = (
            out[: h1_match.start()]
            + h1_match.group(1)
            + name
            + (f" — {sector_txt}" if sector_txt else "")
            + h1_match.group(3)
            + out[h1_match.end() :]
        )

    return out


def _inject_before_body_end(html: str, fragment: str) -> str:
    match = re.search(r"</body>", html, re.I)
    if match:
        pos = match.start()
        return html[:pos] + fragment + html[pos:]
    return html + fragment


def enforce_client_literals_in_html(
    html: str,
    profile: ClientContentProfile,
    *,
    user_prompt: str = "",
) -> str:
    """Corrige title/meta/h1 si le LLM a ignoré l'identité client."""
    if not profile.company_name or "<html" not in (html or "").lower():
        return html

    out = html
    brand = profile.display_name
    name = html_lib.escape(brand)
    sector = html_lib.escape(
        profile.sector_label_for(user_prompt) or "services professionnels"
    )
    city = html_lib.escape(profile.city or "")
    kw = html_lib.escape(", ".join(profile.keywords[:6]))

    title_text = html_lib.escape(
        format_client_page_title(profile, user_prompt=user_prompt, html=html)
    )
    h1_plain = format_client_h1(profile, user_prompt=user_prompt, html=html)

    if re.search(r"<title[^>]*>", out, re.I):
        out = re.sub(
            r"<title[^>]*>[^<]*</title>",
            f"<title>{title_text}</title>",
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    elif re.search(r"<head[^>]*>", out, re.I):
        out = re.sub(
            r"(<head[^>]*>)",
            rf"\1\n<title>{title_text}</title>",
            out,
            count=1,
            flags=re.IGNORECASE,
        )

    desc = f"{name} — {sector}"
    if city:
        desc += f" à {city}"
    if kw:
        desc += f". {kw}"
    if not re.search(r'<meta[^>]+name=["\']description["\']', out, re.I):
        if re.search(r"</title>", out, re.I):
            out = re.sub(
                r"(</title>)",
                rf'\1\n<meta name="description" content="{desc}" />',
                out,
                count=1,
                flags=re.IGNORECASE,
            )
        elif re.search(r"<head[^>]*>", out, re.I):
            out = re.sub(
                r"(<head[^>]*>)",
                rf'\1\n<meta name="description" content="{desc}" />',
                out,
                count=1,
                flags=re.IGNORECASE,
            )

    h1_esc = html_lib.escape(h1_plain)
    for h1_pat in (
        r"(<h1\b[^>]*>)([^<]*)(</h1>)",
        r"(<h1\b[^>]*class=[\"']cf-login-title[\"'][^>]*>)([^<]*)(</h1>)",
    ):
        if re.search(h1_pat, out, re.I):
            out = re.sub(
                h1_pat,
                lambda m: m.group(1) + h1_esc + m.group(3),
                out,
                count=1,
                flags=re.I,
            )
            break

    return out
