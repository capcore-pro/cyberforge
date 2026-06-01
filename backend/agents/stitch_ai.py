"""
StitchAI — maquettes visuelles Google Stitch (HTML + screenshots) avant BuilderAI.

Appelle backend/scripts/stitch_runner.mjs via Node.js.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.base_agent import BaseAgent
from agents.research_agent import ResearchBrief, extract_research_context
from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_RUNNER_PATH = _BACKEND_ROOT / "scripts" / "stitch_runner.mjs"

_SCREEN_SPECS: dict[str, list[tuple[str, str]]] = {
    "vitrine_next": [
        (
            "Accueil",
            "Page d'accueil vitrine premium : hero impactant, proposition de valeur, "
            "CTA principal, navigation claire, footer complet.",
        ),
        (
            "Services",
            "Page services : grille de prestations avec icônes, descriptions courtes, "
            "preuves sociales et bouton de contact.",
        ),
        (
            "Contact",
            "Page contact : formulaire, coordonnées, carte ou zone locale, horaires.",
        ),
    ],
    "ecommerce": [
        (
            "Boutique",
            "Page boutique e-commerce : grille produits, filtres, promotions, panier visible.",
        ),
        (
            "Fiche produit",
            "Fiche produit : galerie images, prix, variantes, ajout au panier, avis clients.",
        ),
        (
            "Panier",
            "Panier et checkout : récapitulatif, livraison, paiement sécurisé.",
        ),
    ],
    "site_reservation": [
        (
            "Accueil",
            "Accueil réservation : hero, créneaux disponibles, avantages, témoignages.",
        ),
        (
            "Réservation",
            "Page réservation : calendrier, sélection créneau, formulaire client.",
        ),
        (
            "Confirmation",
            "Confirmation : récapitulatif réservation, instructions, contact.",
        ),
    ],
    "application_web": [
        (
            "Dashboard",
            "Dashboard application web : sidebar, KPIs, graphiques, actions rapides.",
        ),
        (
            "Liste",
            "Vue liste : tableau ou cartes, filtres, recherche, pagination.",
        ),
        (
            "Détail",
            "Vue détail : fiche entité, actions, historique, métadonnées.",
        ),
    ],
}

_DEFAULT_SECTIONS = ("hero", "services", "contact", "footer")


class StitchMockup(BaseModel):
    name: str
    html_url: str = ""
    image_url: str = ""
    screen_id: str | None = None


class StitchResult(BaseModel):
    """Résultat StitchAI."""

    agent_id: str = "stitch"
    agent_name: str = "StitchAI"
    success: bool = False
    project_id: str | None = None
    mockups: list[StitchMockup] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None


def resolve_stitch_project_type(
    *,
    generation_mode: str | None,
    plan: ArchitectPlan | None,
) -> str:
    mode = (generation_mode or "client_demo").strip()
    if mode == "vitrine_next":
        return "vitrine_next"
    if mode == "real_app":
        return "application_web"
    template = (plan.template if plan else "") or ""
    lower = template.lower()
    if "ecommerce" in lower or "shop" in lower:
        return "ecommerce"
    if "reservation" in lower or "booking" in lower:
        return "site_reservation"
    if plan and plan.project_type.value == "application_web":
        return "application_web"
    return "vitrine_next"


def _palette_dict(plan: ArchitectPlan | None) -> dict[str, str]:
    if not plan or not plan.palette:
        return {}
    p: ToolboxPalette = plan.palette
    return {
        "primary": p.primary,
        "secondary": p.secondary,
        "accent": p.accent,
    }


def _research_content_dict(brief: ResearchBrief | Any | None) -> dict[str, Any]:
    if brief is None:
        return {}
    if isinstance(brief, ResearchBrief):
        return brief.model_dump()
    if hasattr(brief, "model_dump"):
        return brief.model_dump()
    if isinstance(brief, dict):
        return brief
    return {}


def _research_summary(research_content: dict[str, Any]) -> str:
    if not research_content or research_content.get("skipped"):
        return ""
    parts: list[str] = []
    for key, label in (
        ("tendances", "Tendances"),
        ("concurrents", "Concurrents"),
        ("mots_cles", "Mots-clés"),
        ("contenu_suggere", "Contenu"),
        ("exemples_sites", "Exemples"),
    ):
        items = research_content.get(key)
        if isinstance(items, list) and items:
            parts.append(f"{label}: " + "; ".join(str(i) for i in items[:5]))
    secteur = research_content.get("secteur")
    if secteur:
        parts.insert(0, f"Secteur: {secteur}")
    return "\n".join(parts)


def build_screen_prompts(
    *,
    project_type: str,
    sector: str,
    client_name: str,
    palette: dict[str, str],
    sections: list[str],
    research_content: dict[str, Any],
) -> list[dict[str, str]]:
    specs = _SCREEN_SPECS.get(project_type) or _SCREEN_SPECS["vitrine_next"]
    research_block = _research_summary(research_content)
    palette_line = ""
    if palette:
        palette_line = (
            f"Palette obligatoire — primaire {palette.get('primary', '#111827')}, "
            f"secondaire {palette.get('secondary', '#374151')}, "
            f"accent {palette.get('accent', '#d97706')}. "
        )
    sector_line = f"Secteur : {sector}. " if sector else ""
    client_line = f"Marque / client : {client_name}. " if client_name else ""
    sections_line = (
        f"Sections à couvrir sur le site : {', '.join(sections)}. "
        if sections
        else ""
    )
    keywords = research_content.get("mots_cles") if research_content else None
    kw_line = ""
    if isinstance(keywords, list) and keywords:
        kw_line = f"Mots-clés SEO à intégrer visuellement : {', '.join(keywords[:12])}. "

    screens: list[dict[str, str]] = []
    for name, base_prompt in specs:
        prompt = (
            f"{client_line}{sector_line}{palette_line}{sections_line}{kw_line}"
            f"{base_prompt} "
            f"Design professionnel, moderne, accessible, en français. "
            f"UI haute fidélité prête pour implémentation React/HTML."
        )
        if research_block:
            prompt += f"\n\nContexte marché:\n{research_block}"
        screens.append({"name": name, "prompt": prompt.strip(), "device_type": "DESKTOP"})
    return screens


def format_stitch_mockups_for_prompt(result: StitchResult | None) -> str:
    if result is None or result.skipped or not result.success or not result.mockups:
        return ""
    lines = [
        "## Maquettes StitchAI (référence visuelle obligatoire)",
        "Reproduis fidèlement la structure, la hiérarchie visuelle et le style "
        "de ces maquettes dans le code généré.",
        "",
    ]
    for mockup in result.mockups:
        lines.append(f"### {mockup.name}")
        if mockup.image_url:
            lines.append(f"- Capture : {mockup.image_url}")
        if mockup.html_url:
            lines.append(f"- HTML maquette : {mockup.html_url}")
        lines.append("")
    return "\n".join(lines).strip() + "\n\n"


def _resolve_stitch_api_key(settings: Settings) -> str:
    try:
        from security.secret_vault import get_secret_vault

        vault_val = get_secret_vault().peek("STITCH_API_KEY")
        if vault_val:
            return vault_val.strip()
    except Exception:
        pass
    return plain_secret_str(settings.stitch_api_key)


def _run_stitch_runner(payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    env = {**os.environ, "STITCH_API_KEY": str(payload.get("_api_key") or "")}
    payload_clean = {k: v for k, v in payload.items() if k != "_api_key"}
    proc = subprocess.run(
        ["node", str(_RUNNER_PATH)],
        input=json.dumps(payload_clean, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_BACKEND_ROOT),
        env=env,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if not stdout:
        raise RuntimeError(stderr or f"Stitch runner exit {proc.returncode}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Réponse Stitch invalide: {stdout[:300]}") from exc


class StitchAgent(BaseAgent):
    """Génère des maquettes Google Stitch via stitch_runner.mjs."""

    @property
    def agent_id(self) -> str:
        return "stitch"

    @property
    def name(self) -> str:
        return "StitchAI"

    def is_configured(self) -> bool:
        return bool(_resolve_stitch_api_key(self._settings))

    async def run(self, prompt: str, **kwargs: Any) -> str:
        plan = kwargs.get("architect_plan")
        result = await self.generate_mockups(
            architect_plan=plan if isinstance(plan, ArchitectPlan) else None,
            generation_mode=kwargs.get("generation_mode"),
            research_brief=kwargs.get("research_brief"),
            user_prompt=prompt,
        )
        return result.model_dump_json()

    async def generate_mockups(
        self,
        *,
        architect_plan: ArchitectPlan | None,
        generation_mode: str | None = None,
        research_brief: ResearchBrief | Any | None = None,
        user_prompt: str = "",
        sections: list[str] | None = None,
        settings: Settings | None = None,
        on_progress: Any | None = None,
    ) -> StitchResult:
        resolved = settings or self._settings
        if not resolved.stitch_enabled:
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason="StitchAI désactivé",
            )

        api_key = _resolve_stitch_api_key(resolved)
        if not api_key:
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason="STITCH_API_KEY non configurée",
            )

        if not _RUNNER_PATH.is_file():
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason="stitch_runner.mjs introuvable",
            )

        ctx = extract_research_context(
            user_prompt,
            plan=architect_plan,
        )
        project_type = resolve_stitch_project_type(
            generation_mode=generation_mode,
            plan=architect_plan,
        )
        research_content = _research_content_dict(research_brief)
        sector = (
            research_content.get("secteur")
            or ctx.get("secteur")
            or "activité locale"
        )
        client_name = (
            research_content.get("nom_entreprise")
            or ctx.get("nom_entreprise")
            or "Client"
        )
        section_list = list(sections) if sections else list(_DEFAULT_SECTIONS)
        palette = _palette_dict(architect_plan)

        screen_payloads = build_screen_prompts(
            project_type=project_type,
            sector=str(sector),
            client_name=str(client_name),
            palette=palette,
            sections=section_list,
            research_content=research_content,
        )

        mockups: list[StitchMockup] = []
        project_id: str | None = None
        timeout = resolved.stitch_timeout_seconds

        try:
            for index, screen_spec in enumerate(screen_payloads):
                if on_progress:
                    maybe = on_progress(
                        f"Maquette {index + 1}/{len(screen_payloads)} : "
                        f"{screen_spec['name']}…"
                    )
                    if asyncio.iscoroutine(maybe):
                        await maybe

                runner_in = {
                    "_api_key": api_key,
                    "project_id": project_id,
                    "project_title": f"CyberForge — {client_name}",
                    "client_name": client_name,
                    "screens": [screen_spec],
                }
                raw = await asyncio.to_thread(
                    _run_stitch_runner,
                    runner_in,
                    timeout=timeout,
                )
                if not raw.get("success"):
                    err = raw.get("error") or "échec Stitch"
                    if not mockups:
                        return StitchResult(
                            success=False,
                            error=str(err),
                            mockups=[],
                        )
                    logger.warning("Stitch écran %s ignoré: %s", screen_spec["name"], err)
                    continue

                project_id = raw.get("project_id") or project_id
                for item in raw.get("mockups") or []:
                    if not isinstance(item, dict):
                        continue
                    mockups.append(
                        StitchMockup(
                            name=str(item.get("name") or screen_spec["name"]),
                            html_url=str(item.get("html_url") or ""),
                            image_url=str(item.get("image_url") or ""),
                            screen_id=item.get("screen_id"),
                        )
                    )

            if not mockups:
                return StitchResult(
                    success=False,
                    error="Aucune maquette Stitch générée",
                    project_id=project_id,
                )

            return StitchResult(
                success=True,
                project_id=project_id,
                mockups=mockups,
            )
        except subprocess.TimeoutExpired:
            return StitchResult(
                success=False,
                error="timeout Stitch",
                project_id=project_id,
                mockups=mockups,
            )
        except FileNotFoundError:
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason="Node.js non installé",
            )
        except Exception as exc:
            logger.exception("StitchAgent")
            if mockups:
                return StitchResult(
                    success=True,
                    project_id=project_id,
                    mockups=mockups,
                    error=str(exc)[:200],
                )
            return StitchResult(
                success=False,
                error=str(exc)[:400],
            )
