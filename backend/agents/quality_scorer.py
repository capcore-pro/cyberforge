"""
Quality Scorer — scores déterministes 0-100 sur les livrables agents.
"""

from __future__ import annotations

import re
from typing import Any

from agents.supervisor_ai import (
    _CALENDAR_MARKUP_RE,
    _client_name_matches_text,
    _has_footer_markup,
    _is_ecommerce_brief,
    _is_site_reservation_brief,
)


class QualityScorer:
    """Calcule un score 0-100 sur chaque livrable (pas de LLM)."""

    @staticmethod
    def score_html(html: str, brief: dict[str, Any]) -> int:
        body = html or ""
        low = body.lower()
        b = brief or {}
        score = 0

        length = len(body)
        if length > 5000:
            score += 5
        if length > 10000:
            score += 5
        if length > 20000:
            score += 5
        if ":root" in low:
            score += 5
        if "--color-primary" in low:
            score += 5
        if re.search(
            r"fonts\.googleapis\.com|fonts\.google\.com|@import\s+url\([^)]*fonts",
            body,
            re.I,
        ):
            score += 5

        client_name = str(b.get("client_name") or "").strip()
        title_m = re.search(r"<title[^>]*>([^<]*)</title>", body, re.I)
        title_text = (title_m.group(1) or "") if title_m else ""
        if client_name and title_text and _client_name_matches_text(client_name, title_text):
            score += 10

        hero_block = re.search(
            r"<(?:section|div|header)[^>]*(?:id|class)=[\"'][^\"']*hero[^\"']*[\"'][^>]*>",
            body,
            re.I,
        )
        has_hero = bool(hero_block) or 'class="hero"' in low or "class='hero'" in low
        if has_hero:
            hero_snippet = body[hero_block.start() : hero_block.start() + 800] if hero_block else ""
            hidden = bool(re.search(r"display\s*:\s*none", hero_snippet, re.I))
            if not hidden:
                score += 10

        if _has_footer_markup(body, low):
            score += 10

        section_count = len(re.findall(r"<section\b", body, re.I))
        if section_count >= 3:
            score += 10

        if re.search(r"<img\b[^>]*\bpexels-inject\b", body, re.I) or "pexels-inject" in low:
            score += 10

        if _is_site_reservation_brief(b):
            if _CALENDAR_MARKUP_RE.search(body):
                score += 20
        elif _is_ecommerce_brief(b):
            if any(
                token in low
                for token in (
                    "addtocart",
                    "add-to-cart",
                    "stripe",
                    "checkout",
                    "panier",
                    "cart",
                )
            ):
                score += 20
        else:
            score += 20

        return min(100, max(0, score))

    @staticmethod
    def score_brief(brief: dict[str, Any]) -> int:
        b = brief or {}
        score = 0
        description = str(b.get("description") or "")
        if len(description) > 100:
            score += 20
        if len(description) > 200:
            score += 10

        services = b.get("services")
        if isinstance(services, list) and len(services) > 3:
            score += 20

        if str(b.get("ville") or "").strip():
            score += 15
        if str(b.get("email") or "").strip():
            score += 15
        if str(b.get("phone") or "").strip():
            score += 10

        seo = b.get("mots_cles_seo")
        if isinstance(seo, list) and any(str(x).strip() for x in seo):
            score += 10

        return min(100, max(0, score))

    @staticmethod
    def score_deployment(url: str, html_score: int) -> int:
        score = 0
        target = (url or "").strip()
        if target.startswith("https://"):
            score += 50
        if "pages.dev" in target:
            score += 30
        score += min(20, max(0, int(html_score) // 5))
        return min(100, max(0, score))
