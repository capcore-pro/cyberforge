"""
ContentAI — valeurs de placeholders par famille de template (ecommerce, réservation, app, desktop).
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

from tools.client_content_profile import (
    build_client_content_profile,
    humanize_sector_label,
    resolve_client_business_name,
    sanitize_city,
)

_ECOMMERCE_CATEGORIES: dict[str, tuple[str, str, str]] = {
    "ecommerce_alimentaire": (
        "Pains artisanaux",
        "Viennoiseries",
        "Pâtisseries",
    ),
    "ecommerce_mode": ("Nouveautés", "Femme", "Homme"),
    "ecommerce_default": ("Best-sellers", "Promotions", "Cadeaux"),
}

# Mots-clés ResearchAI / brief — jamais en libellés de rayons boutique
_BLOCKED_CATEGORY_KEYWORDS: frozenset[str] = frozenset(
    {
        "solution",
        "solutions",
        "saas",
        "dashboard",
        "logiciel",
        "software",
        "app",
        "application",
        "startup",
        "tech",
        "digital",
        "cloud",
        "api",
        "crm",
        "erp",
        "platform",
        "plateforme",
    }
)

_ECOMMERCE_PRODUCTS: dict[str, list[tuple[str, str]]] = {
    "ecommerce_alimentaire": [
        ("Pain au levain bio", "4,90"),
        ("Croissant pur beurre", "1,40"),
        ("Tarte aux pommes", "18,00"),
        ("Panier découverte", "24,90"),
        ("Confiture maison", "6,50"),
        ("Baguette tradition", "1,20"),
    ],
    "ecommerce_mode": [
        ("Veste laine camel", "189,00"),
        ("Jean slim indigo", "79,00"),
        ("Robe midi satin", "129,00"),
        ("Pull col roulé", "59,00"),
        ("Sac cuir bandoulière", "149,00"),
        ("Chemise oxford", "69,00"),
    ],
    "ecommerce_default": [
        ("Pack Essentiel", "49,00"),
        ("Offre Premium", "89,00"),
        ("Accessoire pro", "29,00"),
        ("Kit découverte", "39,00"),
        ("Abonnement mensuel", "19,90"),
        ("Service express", "15,00"),
    ],
}

_RESERVATION_SERVICES: dict[str, list[tuple[str, str, str]]] = {
    "reservation_sante": [
        ("Consultation générale", "30 min", "55"),
        ("Bilan de santé", "45 min", "80"),
        ("Suivi personnalisé", "20 min", "40"),
    ],
    "reservation_beaute": [
        ("Coupe femme", "45 min", "45"),
        ("Coloration", "1 h 30", "80"),
        ("Balayage", "2 h", "95"),
    ],
    "reservation_default": [
        ("Rendez-vous standard", "30 min", "45"),
        ("Consultation approfondie", "60 min", "75"),
        ("Suivi express", "15 min", "25"),
    ],
}

# Libellés de navigation / rayons (jamais mots-clés ResearchAI type « saas »).
_RESERVATION_SERVICE_NAV: dict[str, tuple[str, str, str]] = {
    "reservation_beaute": ("Coupes", "Colorations", "Soins"),
    "reservation_sante": ("Consultations", "Bilans", "Suivi"),
    "reservation_default": ("Services", "Formules", "Express"),
}

_BLOCKED_RESERVATION_SERVICE_KEYWORDS: frozenset[str] = frozenset(
    {
        "pack",
        "essentiel",
        "premium",
        "produit",
        "standard",
        "saas",
        "solution",
        "dashboard",
        "ecommerce",
        "boutique",
    }
)

_APP_STATS: dict[str, list[tuple[str, str]]] = {
    "app_dashboard": [
        ("Revenus du mois", "24 580 €"),
        ("Nouveaux clients", "128"),
        ("Taux conversion", "3,8 %"),
        ("Tickets ouverts", "12"),
    ],
    "app_dashboard_garage": [
        ("Réparations en cours", "12"),
        ("Véhicules au parc", "28"),
        ("Factures du mois", "156"),
        ("Mécaniciens actifs", "6"),
    ],
    "app_crm": [
        ("Prospects actifs", "86"),
        ("Deals en cours", "14"),
        ("Taux closing", "32 %"),
        ("Relances du jour", "9"),
    ],
    "app_default": [
        ("Utilisateurs actifs", "1 240"),
        ("Sessions / jour", "3 450"),
        ("Satisfaction", "4,7 / 5"),
        ("Alertes", "3"),
    ],
}

_DESKTOP_MODULES: dict[str, tuple[str, str, str]] = {
    "desktop_artisan": ("Devis & chantiers", "Clients", "Planning"),
    "desktop_gestion": ("Facturation", "Stocks", "Rapports"),
    "desktop_default": ("Tableau de bord", "Données", "Paramètres"),
}

# Ville (clé lower) → (adresse affichée, téléphone indicatif local)
_CITY_CONTACT: dict[str, tuple[str, str]] = {
    "rouen": ("Rouen, Normandie", "02 35 XX XX XX"),
    "le havre": ("Le Havre, Normandie", "02 35 XX XX XX"),
    "havre": ("Le Havre, Normandie", "02 35 XX XX XX"),
    "caen": ("Caen, Normandie", "02 31 XX XX XX"),
    "cherbourg": ("Cherbourg, Normandie", "02 33 XX XX XX"),
    "dieppe": ("Dieppe, Normandie", "02 35 XX XX XX"),
    "évreux": ("Évreux, Normandie", "02 32 XX XX XX"),
    "evreux": ("Évreux, Normandie", "02 32 XX XX XX"),
    "alençon": ("Alençon, Normandie", "02 33 XX XX XX"),
    "alencon": ("Alençon, Normandie", "02 33 XX XX XX"),
}


def _contact_email_slug(brand: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", (brand or "").lower())
    return slug[:24] or "contact"


def _resolve_city_for_contact(
    city: str,
    *,
    user_prompt: str = "",
    research: dict[str, Any] | None = None,
) -> str:
    """Ville exploitable pour adresse / téléphone (jamais « votre ville »)."""
    city_clean = sanitize_city(city)
    if city_clean and city_clean.lower() != "votre ville":
        return city_clean
    if research:
        city_clean = sanitize_city(str(research.get("ville") or ""))
        if city_clean:
            return city_clean
    try:
        from agents.research_agent import _extract_city

        return sanitize_city(_extract_city(user_prompt))
    except Exception:
        return ""


def build_default_contact_slots(
    brand: str,
    city: str = "",
    *,
    user_prompt: str = "",
    research: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Valeurs par défaut crédibles pour {{ADDRESS}}, {{EMAIL}}, {{PHONE}}.
    Ne bloque jamais le pipeline — le client ajuste via le CMS après livraison.
    """
    city_resolved = _resolve_city_for_contact(
        city, user_prompt=user_prompt, research=research
    )
    city_key = city_resolved.lower()
    mapped = _CITY_CONTACT.get(city_key)
    if mapped:
        address, phone = mapped
    elif city_resolved:
        address = f"{city_resolved}, France"
        phone = "À préciser"
    else:
        address = "France"
        phone = "À préciser"

    email = f"contact@{_contact_email_slug(brand)}.fr"
    return {
        "PHONE": html_lib.escape(phone),
        "EMAIL": html_lib.escape(email),
        "ADDRESS": html_lib.escape(address),
    }


def ensure_contact_slots(
    slots: dict[str, str],
    brand: str,
    city: str = "",
    *,
    user_prompt: str = "",
    research: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Complète les slots contact manquants sans écraser une valeur déjà fournie."""
    defaults = build_default_contact_slots(
        brand, city, user_prompt=user_prompt, research=research
    )
    for key, value in defaults.items():
        if not (slots.get(key) or "").strip():
            slots[key] = value
    return slots


def _is_usable_category_keyword(keyword: str) -> bool:
    token = (keyword or "").strip().lower()
    if len(token) < 3 or len(token) > 32:
        return False
    if token in _BLOCKED_CATEGORY_KEYWORDS:
        return False
    if any(blocked in token.split() for blocked in _BLOCKED_CATEGORY_KEYWORDS):
        return False
    return True


def _resolve_ecommerce_categories(
    template_id: str,
    research: dict[str, Any],
) -> tuple[str, str, str]:
    """Rayons catalogue — fixes pour l'alimentaire ; filtrage anti-mots-clés tech."""
    defaults = _ECOMMERCE_CATEGORIES.get(
        template_id, _ECOMMERCE_CATEGORIES["ecommerce_default"]
    )
    if template_id == "ecommerce_alimentaire":
        return defaults

    kws = [
        k
        for k in _research_keywords(research)
        if _is_usable_category_keyword(k)
    ]
    if len(kws) >= 3:
        return (
            kws[0].capitalize(),
            kws[1].capitalize(),
            kws[2].capitalize(),
        )
    if len(kws) == 2:
        return (kws[0].capitalize(), kws[1].capitalize(), defaults[2])
    if len(kws) == 1:
        return (kws[0].capitalize(), defaults[1], defaults[2])
    return defaults


def _research_keywords(research: dict[str, Any], limit: int = 8) -> list[str]:
    raw = research.get("mots_cles") or research.get("keywords") or []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and len(text) >= 2 and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _base_brand_context(
    *,
    client_name: str,
    sector: str,
    city: str,
    research_content: Any | None,
    user_prompt: str,
    design_system_slots: dict[str, str],
) -> tuple[str, str, str, str, dict[str, Any]]:
    research: dict[str, Any] = {}
    if research_content is not None:
        if hasattr(research_content, "model_dump"):
            research = research_content.model_dump()
        elif isinstance(research_content, dict):
            research = research_content

    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_content,
    )
    city_clean = sanitize_city(city or research.get("ville") or profile.city) or "votre ville"
    sector_raw = sector or research.get("secteur") or profile.sector
    brand = resolve_client_business_name(
        client_name or profile.company_name or "",
        sector=str(sector_raw or ""),
        city=city_clean if city_clean != "votre ville" else profile.city,
        user_prompt=user_prompt,
    )
    sector_label = humanize_sector_label(
        sector_raw, profile.keywords, user_prompt=user_prompt
    )
    ds = design_system_slots
    return brand, sector_label, city_clean, str(sector_raw or ""), research


def build_ecommerce_slots(
    template_id: str,
    brand: str,
    city: str,
    ds: dict[str, str],
    research: dict[str, Any],
    *,
    user_prompt: str = "",
) -> dict[str, str]:
    cats = _resolve_ecommerce_categories(template_id, research)
    products = _ECOMMERCE_PRODUCTS.get(template_id, _ECOMMERCE_PRODUCTS["ecommerce_default"])

    slots = {
        "CLIENT_NAME": html_lib.escape(brand),
        "PRIMARY_COLOR": ds.get("PRIMARY_COLOR", "#2563EB"),
        "SECONDARY_COLOR": ds.get("SECONDARY_COLOR", "#F8FAFC"),
        "FONT_HEADING": ds.get("FONT_HEADING", "Inter"),
        "FONT_BODY": ds.get("FONT_BODY", "Inter"),
        "GOOGLE_FONTS_URL": ds.get(
            "GOOGLE_FONTS_URL",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ),
        "CATEGORY_1": html_lib.escape(cats[0]),
        "CATEGORY_2": html_lib.escape(cats[1]),
        "CATEGORY_3": html_lib.escape(cats[2]),
        "SHIPPING_DELAY": html_lib.escape("sous 48 h"),
        "PRODUCT_1_NAME": html_lib.escape(products[0][0]),
        "PRODUCT_1_PRICE": html_lib.escape(products[0][1]),
        "PRODUCT_2_NAME": html_lib.escape(products[1][0]),
        "PRODUCT_2_PRICE": html_lib.escape(products[1][1]),
        "PRODUCT_3_NAME": html_lib.escape(products[2][0]),
        "PRODUCT_3_PRICE": html_lib.escape(products[2][1]),
    }
    return ensure_contact_slots(
        slots,
        brand,
        city,
        user_prompt=user_prompt,
        research=research,
    )


def _is_usable_reservation_service_name(name: str) -> bool:
    token = (name or "").strip().lower()
    if len(token) < 3 or len(token) > 48:
        return False
    return not any(blocked in token for blocked in _BLOCKED_RESERVATION_SERVICE_KEYWORDS)


def _resolve_reservation_services(
    template_id: str,
    research: dict[str, Any],
) -> tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]]:
    """Prestations catalogue — fixes pour beauté ; jamais « Pack Essentiel » / mots-clés tech."""
    defaults = _RESERVATION_SERVICES.get(
        template_id, _RESERVATION_SERVICES["reservation_default"]
    )
    if template_id in ("reservation_beaute", "reservation_sante"):
        return defaults[0], defaults[1], defaults[2]

    kws = _research_keywords(research)
    names = [k.capitalize() for k in kws if _is_usable_reservation_service_name(k)]
    if len(names) >= 3:
        return (
            (names[0], defaults[0][1], defaults[0][2]),
            (names[1], defaults[1][1], defaults[1][2]),
            (names[2], defaults[2][1], defaults[2][2]),
        )
    return defaults[0], defaults[1], defaults[2]


def build_reservation_slots(
    template_id: str,
    brand: str,
    city: str,
    ds: dict[str, str],
    *,
    user_prompt: str = "",
    research: dict[str, Any] | None = None,
) -> dict[str, str]:
    svc1, svc2, svc3 = _resolve_reservation_services(template_id, research)
    contact = build_default_contact_slots(
        brand, city, user_prompt=user_prompt, research=research
    )
    nav = _RESERVATION_SERVICE_NAV.get(
        template_id, _RESERVATION_SERVICE_NAV["reservation_default"]
    )
    return {
        "CLIENT_NAME": html_lib.escape(brand),
        "PRIMARY_COLOR": ds.get("PRIMARY_COLOR", "#0D9488"),
        "SECONDARY_COLOR": ds.get("SECONDARY_COLOR", "#F0FDFA"),
        "FONT_HEADING": ds.get("FONT_HEADING", "Inter"),
        "FONT_BODY": ds.get("FONT_BODY", "Inter"),
        "GOOGLE_FONTS_URL": ds.get(
            "GOOGLE_FONTS_URL",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ),
        "SERVICE_1": html_lib.escape(svc1[0]),
        "SERVICE_1_DURATION": html_lib.escape(svc1[1]),
        "SERVICE_1_PRICE": html_lib.escape(svc1[2]),
        "SERVICE_2": html_lib.escape(svc2[0]),
        "SERVICE_2_DURATION": html_lib.escape(svc2[1]),
        "SERVICE_2_PRICE": html_lib.escape(svc2[2]),
        "SERVICE_3": html_lib.escape(svc3[0]),
        "SERVICE_3_DURATION": html_lib.escape(svc3[1]),
        "SERVICE_3_PRICE": html_lib.escape(svc3[2]),
        "NAV_SERVICES": html_lib.escape("Services"),
        "NAV_TARIFS": html_lib.escape("Tarifs"),
        "NAV_RESERVATION": html_lib.escape("Réservation"),
        "NAV_CONTACT": html_lib.escape("Contact"),
        "SERVICE_CAT_1": html_lib.escape(nav[0]),
        "SERVICE_CAT_2": html_lib.escape(nav[1]),
        "SERVICE_CAT_3": html_lib.escape(nav[2]),
        **contact,
    }


_APP_GARAGE_KEYWORDS: tuple[str, ...] = (
    "garage",
    "réparation",
    "reparation",
    "véhicule",
    "vehicule",
    "atelier",
    "mécanique",
    "mecanique",
    "automobile",
    "voiture",
    "carrosserie",
)


def _is_garage_app_context(blob: str) -> bool:
    low = (blob or "").lower()
    return any(k in low for k in _APP_GARAGE_KEYWORDS)


def build_app_slots(
    template_id: str,
    brand: str,
    ds: dict[str, str],
    sector_label: str,
    *,
    user_prompt: str = "",
) -> dict[str, str]:
    blob = f"{user_prompt} {sector_label} {brand}".lower()
    garage = template_id == "app_dashboard" and _is_garage_app_context(blob)
    stats_key = "app_dashboard_garage" if garage else template_id
    stats = _APP_STATS.get(stats_key, _APP_STATS.get(template_id, _APP_STATS["app_default"]))
    if len(stats) < 4:
        stats = list(stats) + list(_APP_STATS["app_default"][: 4 - len(stats)])
    app_name = f"{brand} {sector_label}".strip()[:48]
    if garage:
        table_title = "Interventions récentes"
        col_set = ("Véhicule", "Statut", "Montant TTC")
    elif template_id == "app_crm":
        table_title = "Pipeline commercial"
        col_set = ("Prospect", "Étape", "Montant")
    elif template_id == "app_dashboard":
        table_title = "Activité récente"
        col_set = ("Référence", "Statut", "Montant")
    else:
        table_title = "Données"
        col_set = ("Élément", "Statut", "Valeur")
    return {
        "APP_NAME": html_lib.escape(app_name),
        "CLIENT_NAME": html_lib.escape(brand),
        "PRIMARY_COLOR": ds.get("PRIMARY_COLOR", "#6366F1"),
        "SECONDARY_COLOR": ds.get("SECONDARY_COLOR", "#0F172A"),
        "FONT_HEADING": ds.get("FONT_HEADING", "Inter"),
        "FONT_BODY": ds.get("FONT_BODY", "Inter"),
        "GOOGLE_FONTS_URL": ds.get(
            "GOOGLE_FONTS_URL",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        ),
        "STAT_1_LABEL": html_lib.escape(stats[0][0]),
        "STAT_1_VALUE": html_lib.escape(stats[0][1]),
        "STAT_2_LABEL": html_lib.escape(stats[1][0]),
        "STAT_2_VALUE": html_lib.escape(stats[1][1]),
        "STAT_3_LABEL": html_lib.escape(stats[2][0]),
        "STAT_3_VALUE": html_lib.escape(stats[2][1]),
        "STAT_4_LABEL": html_lib.escape(stats[3][0]),
        "STAT_4_VALUE": html_lib.escape(stats[3][1]),
        "TABLE_TITLE": html_lib.escape(table_title),
        "COL_1": html_lib.escape(col_set[0]),
        "COL_2": html_lib.escape(col_set[1]),
        "COL_3": html_lib.escape(col_set[2]),
    }


def build_desktop_slots(
    template_id: str,
    brand: str,
    ds: dict[str, str],
) -> dict[str, str]:
    modules = _DESKTOP_MODULES.get(template_id, _DESKTOP_MODULES["desktop_default"])
    app_name = brand[:40]
    # Libellés modules : texte catalogue (contient « & ») — pas d'escape HTML
    # (sinon &amp; visible dans la sidebar / barre de statut via JS).
    return {
        "APP_NAME": html_lib.escape(app_name),
        "CLIENT_NAME": html_lib.escape(brand),
        "PRIMARY_COLOR": ds.get("PRIMARY_COLOR", "#0078D4"),
        "MODULE_1": modules[0],
        "MODULE_2": modules[1],
        "MODULE_3": modules[2],
    }
