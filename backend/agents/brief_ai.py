"""
BriefAI — enrichit le brief client (Firecrawl optionnel) et produit un brief structuré.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

from agents.llm_usage_utils import usage_from_anthropic_response
from config import get_settings
from security.llm_secrets import get_effective_llm_key
from tools.firecrawl_client import FirecrawlError, firecrawl_scrape

logger = logging.getLogger(__name__)

MODEL = os.getenv("COREMIND_HAIKU_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 2000

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)

SYSTEM_PROMPT = """Tu es BriefAI pour CyberForge.
À partir du prompt client et des données concurrents (si fournies), produis un brief structuré
pour générer un site web premium en français.

Retourne UNIQUEMENT un JSON valide (sans markdown) avec exactement ces clés :
{
  "client_name": str,
  "project_type": str,
  "sector": str,
  "description": str,
  "services": ["...", "..."],
  "couleur_primaire": "#hex",
  "couleur_secondaire": "#hex",
  "font": "Nom police Google Fonts",
  "ville": str,
  "phone": str,
  "email": str,
  "ambiance": str,
  "mots_cles_seo": ["...", "..."],
  "concurrents": ["...", "..."],
  "tendances": ["...", "..."]
}

Règles :
- Utilise les vraies informations du prompt ; invente uniquement ce qui manque (téléphone, email crédibles).
- services : 3 à 6 prestations concrètes du secteur.
- mots_cles_seo : 5 à 10 mots-clés français.
- concurrents / tendances : synthèse courte à partir des scrapes ou du secteur.
""".strip()

_DEFAULT_BRIEF: dict[str, Any] = {
    "client_name": "Mon entreprise",
    "project_type": "vitrine_next",
    "sector": "commerce",
    "description": "",
    "services": [],
    "couleur_primaire": "#2563EB",
    "couleur_secondaire": "#F8FAFC",
    "font": "Inter",
    "ville": "",
    "phone": "",
    "email": "",
    "ambiance": "professionnelle et moderne",
    "mots_cles_seo": [],
    "concurrents": [],
    "tendances": [],
}


def _extract_urls(text: str, limit: int = 2) -> list[str]:
    seen: list[str] = []
    for raw in _URL_RE.findall(text or ""):
        url = raw.rstrip(".,;)")
        if url not in seen:
            seen.append(url)
        if len(seen) >= limit:
            break
    return seen


async def _scrape_competitors(urls: list[str]) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.firecrawl_configured:
        return []
    out: list[dict[str, Any]] = []
    for url in urls[:2]:
        try:
            result = await firecrawl_scrape(url, settings=settings)
            host = urlparse(url).netloc or url
            out.append(
                {
                    "url": url,
                    "host": host,
                    "title": result.title or "",
                    "meta_description": result.meta_description or "",
                    "titres": (result.titres or [])[:8],
                    "descriptions": (result.descriptions or [])[:5],
                    "cta_texts": (result.cta_texts or [])[:6],
                }
            )
        except (FirecrawlError, Exception) as exc:
            logger.warning("[BriefAI] Firecrawl ignoré pour %s: %s", url, exc)
    return out


def _parse_json_response(raw: str) -> dict[str, Any]:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if len(lines) > 2 else lines[1:])
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON introuvable dans la réponse BriefAI")
    return json.loads(cleaned[start : end + 1])


class BriefAI:
    async def run(
        self,
        *,
        prompt: str,
        project_type: str,
        client_name: str = "",
    ) -> dict[str, Any]:
        user_prompt = (prompt or "").strip()
        pt = (project_type or "vitrine_next").strip()
        name_hint = (client_name or "").strip()

        competitor_urls = _extract_urls(user_prompt)
        scrapes = await _scrape_competitors(competitor_urls)

        firecrawl_block = ""
        if scrapes:
            firecrawl_block = (
                "\n\n## Données concurrents (Firecrawl)\n"
                + json.dumps(scrapes, ensure_ascii=False, indent=2)[:6000]
            )
        else:
            firecrawl_block = "\n\n## Firecrawl\nNon configuré ou aucune URL — continue sans scrape."

        user_message = (
            f"## Prompt client\n{user_prompt}\n\n"
            f"## project_type\n{pt}\n\n"
            f"## client_name (indice)\n{name_hint or '(à déduire du prompt)'}"
            f"{firecrawl_block}"
        )

        api_key = get_effective_llm_key("ANTHROPIC_API_KEY", get_settings())
        if not api_key:
            logger.warning("[BriefAI] ANTHROPIC_API_KEY absente — brief minimal")
            brief = dict(_DEFAULT_BRIEF)
            brief["project_type"] = pt
            if name_hint:
                brief["client_name"] = name_hint
            brief["description"] = user_prompt[:500]
            return brief

        client = anthropic.Anthropic(api_key=api_key)

        def _call():
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            parts: list[str] = []
            for block in response.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts), response

        usage: dict[str, Any] | None = None
        try:
            raw, response = await asyncio.to_thread(_call)
            usage = usage_from_anthropic_response(response, MODEL)
            parsed = _parse_json_response(raw)
        except anthropic.APIError as exc:
            logger.warning("[BriefAI] Anthropic failed: %s", exc)
            from llm.base_provider import LLMRequest
            from llm.router import llm_router

            llm_response = await llm_router.route(
                LLMRequest(
                    messages=[{"role": "user", "content": user_message}],
                    system_prompt=SYSTEM_PROMPT,
                    model=None,
                    max_tokens=MAX_TOKENS,
                ),
                task_type="brief",
            )
            usage = {
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
                "total_tokens": llm_response.total_tokens,
                "model": llm_response.model,
                "provider": llm_response.provider,
            }
            parsed = _parse_json_response(llm_response.content)
        except Exception as exc:
            logger.warning("[BriefAI] échec Claude — brief minimal: %s", exc)
            parsed = {}

        brief = dict(_DEFAULT_BRIEF)
        for key in _DEFAULT_BRIEF:
            if key in parsed and parsed[key] is not None:
                brief[key] = parsed[key]

        if name_hint:
            brief["client_name"] = name_hint
        brief["project_type"] = str(brief.get("project_type") or pt)
        if not str(brief.get("description") or "").strip():
            brief["description"] = user_prompt[:800]

        for list_key in ("services", "mots_cles_seo", "concurrents", "tendances"):
            val = brief.get(list_key)
            if not isinstance(val, list):
                brief[list_key] = []
            brief[list_key] = [str(x).strip() for x in brief[list_key] if str(x).strip()]

        if usage:
            brief["usage"] = usage
        return brief
