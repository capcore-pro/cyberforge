"""
StitchAI — maquettes visuelles Google Stitch (HTML + screenshots) avant BuilderAI.

Appelle backend/scripts/stitch_runner.mjs via Node.js.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import unicodedata
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
_STITCH_SDK_PACKAGE = _BACKEND_ROOT / "node_modules" / "@google" / "stitch-sdk" / "package.json"
# Plafond strict subprocess + budget total StitchAI (évite coupure SSE).
STITCH_SUBPROCESS_TIMEOUT_SECONDS = 30.0
STITCH_PIPELINE_BUDGET_SECONDS = 30.0

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
    design_system_block: str = "",
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

    law = design_system_block.strip()
    if law and not law.endswith("\n"):
        law += "\n"

    screens: list[dict[str, str]] = []
    for name, base_prompt in specs:
        prompt = (
            f"{law}{client_line}{sector_line}{palette_line}{sections_line}{kw_line}"
            f"{base_prompt} "
            f"Design professionnel, moderne, accessible, en français. "
            f"UI haute fidélité prête pour implémentation React/HTML. "
            f"Respecter strictement la loi visuelle DesignSystemAI ci-dessus."
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


_ASCII_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("\u2192", "->"),
    ("\u2190", "<-"),
    ("\u2194", "<->"),
    ("\u2014", "-"),
    ("\u2013", "-"),
    ("\u2026", "..."),
    ("\u00ab", '"'),
    ("\u00bb", '"'),
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
)


def _sanitize_ascii_text(text: str) -> str:
    """Retire les caractères non-ASCII (évite charmap cp1252 sur Windows)."""
    if not text:
        return text
    cleaned = text
    for src, dst in _ASCII_REPLACEMENTS:
        cleaned = cleaned.replace(src, dst)
    normalized = unicodedata.normalize("NFKD", cleaned)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _sanitize_runner_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_ascii_text(value)
    if isinstance(value, dict):
        return {str(k): _sanitize_runner_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_runner_payload(item) for item in value]
    return value


def _stitch_subprocess_timeout(configured: float | None = None) -> float:
    """Timeout effectif du subprocess Node (max 30 s)."""
    if configured is None or configured <= 0:
        return STITCH_SUBPROCESS_TIMEOUT_SECONDS
    return min(float(configured), STITCH_SUBPROCESS_TIMEOUT_SECONDS)


def _stitch_verbose() -> bool:
    return os.environ.get("STITCH_VERBOSE", "").strip().lower() in ("1", "true", "yes")


def _try_install_stitch_sdk() -> bool:
    """Installe @google/stitch-sdk dans backend/ si absent (silencieux)."""
    if _STITCH_SDK_PACKAGE.is_file():
        return True
    npm = shutil.which("npm")
    if npm is None:
        return False
    try:
        subprocess.run(
            [npm, "install", "@google/stitch-sdk", "--no-audit", "--no-fund"],
            cwd=str(_BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.debug("[StitchAI] npm install @google/stitch-sdk échoué", exc_info=True)
    return _STITCH_SDK_PACKAGE.is_file()


def _stitch_node_deps_ready() -> tuple[bool, str]:
    """Vérifie Node.js, le runner et @google/stitch-sdk (npm install dans backend/)."""
    if shutil.which("node") is None:
        return False, "Node.js introuvable dans le PATH"
    if not _RUNNER_PATH.is_file():
        return False, f"Runner introuvable : {_RUNNER_PATH}"
    if not _STITCH_SDK_PACKAGE.is_file():
        if _try_install_stitch_sdk():
            return True, ""
        return (
            False,
            "@google/stitch-sdk absent — exécutez « npm install » dans le dossier backend/",
        )
    return True, ""


def _stitch_degraded_result(error: str) -> StitchResult:
    """Mode dégradé : le pipeline continue sans maquettes."""
    return StitchResult(success=False, mockups=[], error=error)


def _stitch_subprocess_env(api_key: str) -> dict[str, str]:
    return {
        **os.environ,
        "STITCH_API_KEY": api_key,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _resolve_stitch_api_key(settings: Settings) -> str:
    try:
        from security.secret_vault import get_secret_vault

        vault_val = get_secret_vault().peek("STITCH_API_KEY")
        if vault_val:
            return vault_val.strip()
    except Exception:
        pass
    return plain_secret_str(settings.stitch_api_key)


def _stitch_console(message: str) -> None:
    """Logs détaillés uniquement si STITCH_VERBOSE=1."""
    if _stitch_verbose():
        logger.info("%s", message)
        print(message, flush=True)


def _log_stitch_runner_payload(payload_clean: dict[str, Any], *, timeout: float) -> None:
    if not _stitch_verbose():
        return
    payload_json = json.dumps(payload_clean, ensure_ascii=True, indent=2)
    _stitch_console(
        f"[StitchAI] subprocess Node.js — préparation | runner={_RUNNER_PATH} | "
        f"cwd={_BACKEND_ROOT} | timeout={timeout:.1f}s"
    )
    _stitch_console(f"[StitchAI] payload JSON envoyé au runner:\n{payload_json}")


def _log_stitch_subprocess_result(
    proc: subprocess.CompletedProcess[str],
    *,
    stdout: str,
    stderr: str,
) -> None:
    if not _stitch_verbose():
        logger.debug(
            "[StitchAI] subprocess terminé | returncode=%s | stdout_len=%d | stderr_len=%d",
            proc.returncode,
            len(stdout),
            len(stderr),
        )
        return
    _stitch_console(
        f"[StitchAI] subprocess terminé | returncode={proc.returncode} | "
        f"stdout_len={len(stdout)} | stderr_len={len(stderr)}"
    )
    _stitch_console(f"[StitchAI] stdout (contenu exact):\n{stdout if stdout else '(vide)'}")
    _stitch_console(f"[StitchAI] stderr (contenu exact):\n{stderr if stderr else '(vide)'}")


def _run_stitch_runner(payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    api_key = str(payload.get("_api_key") or "")
    payload_clean = _sanitize_runner_payload(
        {k: v for k, v in payload.items() if k != "_api_key"}
    )
    input_json = json.dumps(payload_clean, ensure_ascii=True)
    _log_stitch_runner_payload(payload_clean, timeout=timeout)
    if _stitch_verbose():
        _stitch_console(
            f"[StitchAI] commande: node {_RUNNER_PATH.name} | stdin_json_len={len(input_json)} | "
            f"api_key_configured={bool(api_key)}"
        )

    try:
        proc = subprocess.run(
            ["node", str(_RUNNER_PATH)],
            input=input_json,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(_BACKEND_ROOT),
            env=_stitch_subprocess_env(api_key),
        )
    except subprocess.TimeoutExpired:
        logger.debug("[StitchAI] subprocess timeout après %.1fs", timeout)
        raise

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    _log_stitch_subprocess_result(proc, stdout=stdout, stderr=stderr)

    if not stdout:
        logger.error(
            "[StitchAI] échec: stdout vide (returncode=%s) — voir stderr ci-dessus",
            proc.returncode,
        )
        raise RuntimeError(stderr or f"Stitch runner exit {proc.returncode}")
    try:
        parsed = json.loads(stdout)
        logger.info(
            "[StitchAI] réponse JSON parsée | success=%s | keys=%s",
            parsed.get("success"),
            list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
        )
        return parsed
    except json.JSONDecodeError as exc:
        logger.error(
            "[StitchAI] JSON stdout invalide: %s | extrait=%r",
            exc,
            stdout[:500],
        )
        raise RuntimeError(f"Réponse Stitch invalide: {stdout[:300]}") from exc


async def _invoke_stitch_runner(
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    """Subprocess Node avec timeout strict ; relève TimeoutError si dépassé."""
    effective = _stitch_subprocess_timeout(timeout)
    return await asyncio.wait_for(
        asyncio.to_thread(_run_stitch_runner, payload, timeout=effective),
        timeout=effective + 5.0,
    )


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
        design_system: dict[str, Any] | None = None,
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

        deps_ok, deps_reason = _stitch_node_deps_ready()
        if not deps_ok:
            logger.debug("[StitchAI] prérequis manquants: %s", deps_reason)
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason=deps_reason,
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
        from agents.design_system_ai import (
            design_system_to_stitch_palette,
            format_design_system_for_prompt,
        )

        palette = design_system_to_stitch_palette(design_system)
        if not palette:
            palette = _palette_dict(architect_plan)
        design_block = format_design_system_for_prompt(design_system)

        screen_payloads = build_screen_prompts(
            project_type=project_type,
            sector=str(sector),
            client_name=str(client_name),
            palette=palette,
            sections=section_list,
            research_content=research_content,
            design_system_block=design_block,
        )
        configured_timeout = resolved.stitch_timeout_seconds
        subprocess_cap = _stitch_subprocess_timeout(configured_timeout)
        logger.info(
            "[StitchAI] generate_mockups | project_type=%s | client=%s | screens=%d | "
            "subprocess_timeout=%.1fs | pipeline_budget=%.1fs",
            project_type,
            client_name,
            len(screen_payloads),
            subprocess_cap,
            STITCH_PIPELINE_BUDGET_SECONDS,
        )

        mockups: list[StitchMockup] = []
        project_id: str | None = None
        deadline = time.monotonic() + STITCH_PIPELINE_BUDGET_SECONDS

        try:
            for index, screen_spec in enumerate(screen_payloads):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.debug("[StitchAI] budget pipeline épuisé — mode dégradé")
                    return _stitch_degraded_result("timeout")

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
                run_timeout = min(remaining, subprocess_cap)
                logger.info(
                    "[StitchAI] écran %d/%d | name=%s | project_id=%s | timeout=%.1fs",
                    index + 1,
                    len(screen_payloads),
                    screen_spec.get("name"),
                    project_id or "(nouveau)",
                    run_timeout,
                )
                try:
                    raw = await _invoke_stitch_runner(
                        runner_in,
                        timeout=run_timeout,
                    )
                except (asyncio.TimeoutError, subprocess.TimeoutExpired):
                    logger.debug(
                        "[StitchAI] timeout subprocess (%.0fs) — mode dégradé",
                        run_timeout,
                    )
                    return _stitch_degraded_result("timeout")
                except FileNotFoundError:
                    return StitchResult(
                        success=True,
                        skipped=True,
                        skip_reason="Node.js non installé",
                    )
                except Exception as exc:
                    logger.debug(
                        "[StitchAI] subprocess échoué (écran %s): %s",
                        screen_spec.get("name"),
                        exc,
                    )
                    return _stitch_degraded_result("timeout")

                logger.info(
                    "[StitchAI] écran %s — runner terminé | success=%s",
                    screen_spec.get("name"),
                    raw.get("success"),
                )
                if not raw.get("success"):
                    err = str(raw.get("error") or "échec Stitch").lower()
                    logger.warning(
                        "[StitchAI] écran %s refusé: %s",
                        screen_spec.get("name"),
                        raw.get("error"),
                    )
                    if "timeout" in err or "timed out" in err:
                        return _stitch_degraded_result("timeout")
                    return _stitch_degraded_result(str(raw.get("error") or "échec Stitch"))

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
                return _stitch_degraded_result("Aucune maquette Stitch générée")

            return StitchResult(
                success=True,
                project_id=project_id,
                mockups=mockups,
            )
        except (asyncio.TimeoutError, subprocess.TimeoutExpired):
            logger.debug("[StitchAI] timeout pipeline — mode dégradé")
            return _stitch_degraded_result("timeout")
        except FileNotFoundError:
            return StitchResult(
                success=True,
                skipped=True,
                skip_reason="Node.js non installé",
            )
        except Exception as exc:
            logger.debug("[StitchAI] exception pipeline — mode dégradé: %s", exc)
            return _stitch_degraded_result("timeout")
