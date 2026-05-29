"""VitrineContentAI — génère le JSON site.json depuis un prompt client."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from config import Settings, get_settings
from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    _parse_json_response,
)
from tools.vitrine.content_schema import ClientBranding, VitrineSiteContent
from tools.vitrine.scaffold_renderer import load_example_content

logger = logging.getLogger(__name__)

VITRINE_CONTENT_SYSTEM = """Tu es VitrineContentAI pour CyberForge.
Tu produis le contenu JSON d'un site vitrine multi-pages (français) pour une PME locale.

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown), structure exacte :
{
  "meta": { "businessName", "tagline", "locale": "fr", "primaryColor": "#hex", "logoUrl": null },
  "navigation": [ {"label": "Accueil", "href": "/"}, {"label": "Services", "href": "/services"}, {"label": "Contact", "href": "/contact"} ],
  "home": {
    "hero": { "title", "subtitle", "ctaPrimary": {"label","href"}, "ctaSecondary": {"label","href"}, "image": {"url":"https://images.unsplash.com/placeholder","alt","imageQuery":"requête EN 3-6 mots","photographer":null,"photographerUrl":null} },
    "servicesPreview": [ 3 objets { "title", "description", "href": "/services#id", "image": {"url":"https://images.unsplash.com/placeholder","alt","imageQuery":"…"} } ],
    "testimonials": [ 3 objets { "quote", "author", "role", "rating": 5 } ],
    "ctaBand": { "title", "text", "buttonLabel", "buttonHref": "/contact" }
  },
  "servicesPage": {
    "intro": { "title", "description" },
    "sections": [ 3 objets { "id": "slug-kebab", "title", "description", "bullets": ["..."], "image": {"url":"https://images.unsplash.com/placeholder","alt","imageQuery":"…"} } ]
  },
  "contactPage": {
    "headline", "subtext",
    "fields": { "name", "email", "message", "submit" },
    "successMessage",
    "sidebar": { "phone", "email", "hours", "address" }
  },
  "footer": { "description", "phone", "email", "address", "socialLinks": [], "legalNote" }
}

Règles images : chaque image doit avoir imageQuery (3-6 mots EN, métier + contexte, ex. "plumber fixing sink").
url = placeholder https://images.unsplash.com/placeholder ; alt en français descriptif.
Les href servicesPreview doivent correspondre aux id des sections (ex. /services#depannage).
Ton professionnel, local, rassurant. Pas de lorem ipsum."""


class VitrineContentError(Exception):
    """Échec génération du contenu vitrine."""


class VitrineContentAgent:
    """Génère et valide un VitrineSiteContent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._codegen = CodeGenService(self._settings)

    async def generate(
        self,
        prompt: str,
        *,
        project_type_label: str = "Site vitrine",
        branding: ClientBranding | None = None,
        project_id: str | None = None,
    ) -> VitrineSiteContent:
        cleaned = prompt.strip()
        if len(cleaned) < 3:
            raise VitrineContentError("Le prompt doit contenir au moins 3 caractères.")

        user_msg = (
            f"Type de projet : {project_type_label.strip()}\n"
            f"{_branding_prompt_block(branding)}\n"
            f"Brief client :\n{cleaned[:8000]}"
        )

        previous_track = self._codegen._track_project_id
        self._codegen._track_project_id = project_id
        try:
            raw = await self._generate_full_json(user_msg)
        finally:
            self._codegen._track_project_id = previous_track
        if not raw:
            logger.warning("VitrineContentAI — repli sur exemple site.json")
            content = load_example_content()
            return _apply_branding(content, branding, prompt=cleaned)

        try:
            content = VitrineSiteContent.model_validate(raw)
        except Exception as exc:
            logger.warning("VitrineContentAI — JSON invalide (%s), repli exemple", exc)
            content = load_example_content()
            return _apply_branding(content, branding, prompt=cleaned)

        return _apply_branding(content, branding, prompt=cleaned)

    async def _generate_full_json(self, user_msg: str) -> dict[str, Any] | None:
        specs = self._codegen._available_specs(CodeGenComplexity.MOYENNE)
        if not specs:
            return None

        previous_prompt = self._codegen._active_system_prompt
        self._codegen._active_system_prompt = VITRINE_CONTENT_SYSTEM
        errors: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=self._codegen._http_timeout()) as client:
                for spec in specs:
                    try:
                        text = await spec.call(user_msg, spec.model, client)
                        parsed = _parse_json_response(text)
                        if isinstance(parsed, dict) and "home" in parsed:
                            return parsed
                    except httpx.TimeoutException:
                        errors.append(f"{spec.provider_id}: timeout")
                    except Exception as exc:
                        errors.append(f"{spec.provider_id}: {exc}")
        finally:
            self._codegen._active_system_prompt = previous_prompt

        if errors:
            logger.warning("VitrineContentAI LLM : %s", " | ".join(errors[:3]))
        return None


def _branding_prompt_block(branding: ClientBranding | None) -> str:
    if branding is None:
        return ""
    lines = ["Branding client existant :"]
    if branding.name:
        lines.append(f"- Nom : {branding.name}")
    if branding.company:
        lines.append(f"- Entreprise : {branding.company}")
    if branding.primary_color:
        lines.append(f"- Couleur : {branding.primary_color}")
    if branding.phone:
        lines.append(f"- Téléphone : {branding.phone}")
    if branding.email:
        lines.append(f"- E-mail : {branding.email}")
    return "\n".join(lines)


def _apply_branding(
    content: VitrineSiteContent,
    branding: ClientBranding | None,
    *,
    prompt: str,
) -> VitrineSiteContent:
    data = content.model_dump()
    meta = data["meta"]

    if branding:
        if branding.name or branding.company:
            meta["businessName"] = branding.company or branding.name or meta["businessName"]
        if branding.primary_color:
            meta["primaryColor"] = branding.primary_color
        if branding.logo_url:
            meta["logoUrl"] = branding.logo_url
        footer = data.get("footer") or {}
        if branding.phone:
            footer["phone"] = branding.phone
            data["contactPage"]["sidebar"]["phone"] = branding.phone
        if branding.email:
            footer["email"] = branding.email
            data["contactPage"]["sidebar"]["email"] = branding.email
        data["footer"] = footer

    title_match = re.search(
        r"(?:pour|site vitrine pour|vitrine pour)\s+([^.,\n]+)",
        prompt,
        re.I,
    )
    if title_match and not branding:
        guess = title_match.group(1).strip()
        if len(guess) > 2:
            meta["businessName"] = guess[:80]

    data["meta"] = meta
    return VitrineSiteContent.model_validate(data)


async def generate_vitrine_content(
    prompt: str,
    *,
    project_type_label: str = "Site vitrine",
    branding: ClientBranding | None = None,
    settings: Settings | None = None,
    project_id: str | None = None,
) -> VitrineSiteContent:
    agent = VitrineContentAgent(settings)
    return await agent.generate(
        prompt,
        project_type_label=project_type_label,
        branding=branding,
        project_id=project_id,
    )
