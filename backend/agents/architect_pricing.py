"""
Analyse de complexité et grille tarifaire marché — ArchitectAI.
"""

from __future__ import annotations

import re
from typing import Literal

from agents.coremind_agent import ProjectType

PricingCategory = Literal[
    "vitrine_next",
    "application_web",
    "site_reservation",
    "ecommerce",
    "extension_navigateur",
    "application_desktop",
]

ComplexityTier = Literal["simple", "moyenne", "complexe"]

SUGGESTED_PRICE_RATIO = 0.4

# EUR (min, max) — marché freelance / agence
_MARKET_GRID: dict[PricingCategory, dict[ComplexityTier, tuple[int, int]]] = {
    "vitrine_next": {
        "simple": (300, 600),
        "moyenne": (600, 1200),
        "complexe": (1200, 2500),
    },
    "application_web": {
        "simple": (800, 1500),
        "moyenne": (1500, 3000),
        "complexe": (3000, 8000),
    },
    "site_reservation": {
        "simple": (1000, 2000),
        "moyenne": (2000, 4000),
        "complexe": (4000, 10000),
    },
    "ecommerce": {
        "simple": (1500, 3000),
        "moyenne": (3000, 6000),
        "complexe": (6000, 15000),
    },
    "extension_navigateur": {
        "simple": (500, 1000),
        "moyenne": (1000, 2000),
        "complexe": (2000, 5000),
    },
    "application_desktop": {
        "simple": (1000, 2000),
        "moyenne": (2000, 5000),
        "complexe": (5000, 15000),
    },
}

_FEATURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(auth|authentification|login|connexion|inscription|compte)\b", re.I),
    re.compile(r"\b(paiement|payment|checkout|panier|cart|commande)\b", re.I),
    re.compile(r"\b(dashboard|tableau de bord|admin|back[- ]?office)\b", re.I),
    re.compile(r"\b(notification|email|newsletter|chat|messagerie)\b", re.I),
    re.compile(r"\b(recherche|search|filtre|tri|pagination)\b", re.I),
    re.compile(r"\b(rôle|roles|permission|multi[- ]?utilisateur)\b", re.I),
    re.compile(r"\b(crm|pipeline|devis|facture|abonnement)\b", re.I),
    re.compile(r"\b(carte|map|géoloc|calendrier|agenda)\b", re.I),
    re.compile(r"\b(upload|fichier|média|galerie|pdf)\b", re.I),
    re.compile(r"\b(export|import|csv|excel|rapport)\b", re.I),
)

_INTEGRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(stripe|paypal|mollie|adyen)\b", re.I),
    re.compile(r"\b(google maps|mapbox|openstreetmap)\b", re.I),
    re.compile(r"\b(oauth|google login|facebook login|sso)\b", re.I),
    re.compile(r"\b(webhook|zapier|make\.com|n8n)\b", re.I),
    re.compile(r"\b(api tierce|api externe|intégration|integration)\b", re.I),
    re.compile(r"\b(brevo|sendgrid|mailchimp|twilio|sms)\b", re.I),
    re.compile(r"\b(shopify|woocommerce|prestashop|magento)\b", re.I),
    re.compile(r"\b(algolia|elasticsearch|meilisearch)\b", re.I),
    re.compile(r"\b(s3|cloudinary|firebase|supabase)\b", re.I),
)

_PAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(\d+)\s*(pages?|écrans?|screens?)\b", re.I),
    re.compile(
        r"\b(accueil|home|services?|contact|à propos|about|blog|faq|tarifs?|pricing)\b",
        re.I,
    ),
    re.compile(r"\b(multi[- ]?pages?|plusieurs pages)\b", re.I),
)

_LOGIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(workflow|processus|règle|rules engine)\b", re.I),
    re.compile(r"\b(réservation|booking|créneau|disponibilité|calendrier)\b", re.I),
    re.compile(r"\b(inventaire|stock|catalogue|variante)\b", re.I),
    re.compile(r"\b(calcul|commission|marge|devis automatique)\b", re.I),
    re.compile(r"\b(validation|approbation|état|statut métier)\b", re.I),
    re.compile(r"\b(temps réel|real[- ]?time|websocket|live)\b", re.I),
)

_ECOMMERCE_HINTS = (
    "e-commerce",
    "ecommerce",
    "boutique",
    "shop",
    "panier",
    "checkout",
    "produit",
    "catalogue",
    "woocommerce",
)

_RESERVATION_HINTS = (
    "réservation",
    "reservation",
    "booking",
    "restaurant",
    "table",
    "créneau",
    "couvert",
    "hôtel",
    "chambre",
)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _count_matches(patterns: tuple[re.Pattern[str], ...], text: str) -> int:
    return sum(1 for pattern in patterns if pattern.search(text))


def _extract_page_count(text: str) -> int:
    match = re.search(r"\b(\d+)\s*(?:pages?|écrans?|screens?)\b", text, re.I)
    if match:
        return int(match.group(1))
    section_hits = len(
        re.findall(
            r"\b(accueil|home|services?|contact|à propos|about|blog|faq|tarifs?|pricing)\b",
            text,
            re.I,
        )
    )
    if re.search(r"\b(multi[- ]?pages?|plusieurs pages)\b", text, re.I):
        return max(3, section_hits)
    return section_hits


def analyze_prompt_complexity(prompt: str) -> int:
    """
    Score 1–10 à partir du prompt : fonctionnalités, intégrations, pages, logique métier.
    """
    text = _normalize(prompt)
    if not text:
        return 1

    score = 3
    features = _count_matches(_FEATURE_PATTERNS, text)
    integrations = _count_matches(_INTEGRATION_PATTERNS, text)
    logic = _count_matches(_LOGIC_PATTERNS, text)
    pages = _extract_page_count(text)

    score += min(features, 4)
    score += min(integrations * 2, 4)
    score += min(logic, 3)

    if pages >= 5:
        score += 2
    elif pages >= 3:
        score += 1

    if len(text) > 250:
        score += 1
    if len(text) > 600:
        score += 1

    simple_hints = ("mvp", "prototype", "simple", "landing", "one page", "une page", "vitrine")
    if any(h in text for h in simple_hints) and integrations == 0 and features <= 1:
        score -= 1

    return max(1, min(10, score))


def complexity_label_from_score(score: int) -> str:
    if score <= 3:
        return "Simple"
    if score <= 6:
        return "Moyenne"
    return "Complexe"


def complexity_tier_from_score(score: int) -> ComplexityTier:
    if score <= 3:
        return "simple"
    if score <= 6:
        return "moyenne"
    return "complexe"


def resolve_pricing_category(
    project_type: ProjectType,
    prompt: str,
    *,
    generation_mode: str | None = None,
) -> PricingCategory:
    text = _normalize(prompt)
    mode = (generation_mode or "").strip().lower()

    if mode == "vitrine_next":
        return "vitrine_next"
    if any(h in text for h in _ECOMMERCE_HINTS):
        return "ecommerce"
    if any(h in text for h in _RESERVATION_HINTS):
        return "site_reservation"

    if project_type == ProjectType.EXTENSION_NAVIGATEUR:
        return "extension_navigateur"
    if project_type == ProjectType.APPLICATION_DESKTOP:
        return "application_desktop"
    if project_type in (
        ProjectType.APPLICATION_WEB,
        ProjectType.SAAS_DASHBOARD,
        ProjectType.API_BACKEND,
        ProjectType.APPLICATION_MOBILE,
    ):
        return "application_web"
    if project_type in (ProjectType.SITE_WEB, ProjectType.LANDING_PAGE):
        return "vitrine_next"

    return "application_web"


def estimate_prices(
    category: PricingCategory,
    complexity_score: int,
) -> tuple[int, int, int, int, str]:
    """
    Retourne market_min, market_max, suggested_min, suggested_max, pricing_category.
    """
    tier = complexity_tier_from_score(complexity_score)
    market_min, market_max = _MARKET_GRID[category][tier]
    suggested_min = max(1, int(market_min * SUGGESTED_PRICE_RATIO))
    suggested_max = max(suggested_min, int(market_max * SUGGESTED_PRICE_RATIO))
    return market_min, market_max, suggested_min, suggested_max, category


def build_complexity_pricing(
    prompt: str,
    project_type: ProjectType,
    *,
    generation_mode: str | None = None,
) -> dict[str, int | str]:
    score = analyze_prompt_complexity(prompt)
    category = resolve_pricing_category(
        project_type,
        prompt,
        generation_mode=generation_mode,
    )
    market_min, market_max, suggested_min, suggested_max, _ = estimate_prices(
        category,
        score,
    )
    return {
        "complexity_score": score,
        "complexity_label": complexity_label_from_score(score),
        "market_price_min": market_min,
        "market_price_max": market_max,
        "suggested_price_min": suggested_min,
        "suggested_price_max": suggested_max,
        "pricing_category": category,
    }
