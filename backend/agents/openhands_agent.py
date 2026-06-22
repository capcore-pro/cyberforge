"""
OpenHands Agent — CyberForge
Analyse statique + correction intelligente pour tous types de livrables.
Mode Pipeline : s'insère entre GeneratorAI et SupervisorAI.
Mode Debug    : déclenché manuellement depuis l'interface projet.
API REST directe — zéro SDK — zéro conflit OpenTelemetry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.coremind_agent import ProjectType
from agents.shared_context import SharedContext
from config import Settings, get_settings, plain_secret_str


class _OpenHandsPlan(Protocol):
    complexity_score: int
    project_type: ProjectType

logger = logging.getLogger(__name__)

DEFAULT_OPENHANDS_API_URL = "https://app.all-hands.dev/api/v1"
MAX_CODE_CHARS = 8000

# ─── ANALYSEURS PAR TYPE DE PROJET ────────────────────────────────────────────

PROJECT_ANALYZERS: dict[str, str] = {
    "website": "web",
    "ecommerce": "web",
    "booking": "web",
    "web_app": "web",
    "crm": "web",
    "extension": "extension",
    "desktop": "electron",
    "mobile": "mobile",
    "erp": "erp",
}

CYBERFORGE_PROJECT_TYPE_MAP: dict[str, str] = {
    "site_web": "website",
    "landing_page": "website",
    "vitrine_next": "website",
    "client_demo": "website",
    "ecommerce": "ecommerce",
    "site_reservation": "booking",
    "application_web": "web_app",
    "crm": "crm",
    "real_app": "web_app",
    "extension_navigateur": "extension",
    "application_desktop": "desktop",
    "application_mobile": "mobile",
    "saas_dashboard": "web_app",
    "api_backend": "web_app",
    "projet_generique": "website",
}

# ─── RÈGLES D'ANALYSE PAR TYPE ─────────────────────────────────────────────────

ANALYSIS_RULES: dict[str, list[str]] = {
    "web": [
        "Vérifie que le HTML est valide et bien structuré (doctype, head, body)",
        "Vérifie qu'il n'y a pas de balises non fermées",
        "Vérifie que tous les liens href ne sont pas vides ou cassés (#, undefined, null)",
        "Vérifie que les scripts JS ne contiennent pas d'erreurs de syntaxe évidentes",
        "Vérifie que les variables CSS (--primary, --secondary) sont bien définies",
        "Vérifie que les images ont un attribut alt",
        "Vérifie que le meta viewport est présent pour le responsive",
        "Vérifie que Stripe est correctement injecté si présent (clé publique, checkout)",
        "Vérifie l'absence de console.log en production",
        "Vérifie que les formulaires ont une action ou un handler JS",
    ],
    "extension": [
        "Vérifie que manifest.json est valide Manifest V3",
        "Vérifie que les permissions déclarées sont cohérentes avec le code",
        "Vérifie que background service_worker existe si déclaré",
        "Vérifie que content_scripts pointent vers des fichiers existants",
        "Vérifie l'absence d'API Manifest V2 dépréciées (background.scripts, browser_action)",
    ],
    "electron": [
        "Vérifie que main.js/index.js crée bien une BrowserWindow",
        "Vérifie que preload.js utilise contextBridge correctement",
        "Vérifie que les ipcMain/ipcRenderer sont cohérents entre main et renderer",
        "Vérifie que package.json contient main, build config electron-builder",
        "Vérifie l'absence de require() dans le renderer sans contextBridge",
        "Vérifie que nodeIntegration est false et contextIsolation est true",
    ],
    "mobile": [
        "Vérifie que App.tsx utilise expo-router ou React Navigation correctement",
        "Vérifie qu'il n'y a pas d'imports manquants dans les composants",
        "Vérifie la compatibilité Expo SDK 51 (pas d'API dépréciées)",
        "Vérifie que app.json contient les champs obligatoires (name, slug, version)",
        "Vérifie que les StyleSheet.create() ne contiennent pas de propriétés invalides React Native",
        "Vérifie l'absence de composants web (div, span, p) dans les fichiers .tsx mobile",
    ],
    "erp": [
        "Vérifie que docker-compose.yml est valide YAML",
        "Vérifie que les ports déclarés ne sont pas en conflit",
        "Vérifie que les variables d'environnement critiques sont définies (DB_*, ADMIN_*)",
        "Vérifie que les volumes sont correctement montés",
        "Vérifie que les depends_on sont cohérents avec les services déclarés",
        "Vérifie que les images Docker référencées existent (odoo, postgres, nginx...)",
    ],
}


class OpenHandsAnalysisResult(BaseModel):
    """Résultat structuré d'une itération d'analyse / correction."""

    issues_found: list[str] = Field(default_factory=list)
    corrections_applied: list[str] = Field(default_factory=list)
    corrected_code: str = ""
    quality_score: float = 0.0
    summary: str = ""
    source: str = "local_fallback"
    iteration: int = 1


def normalize_project_type(project_type: str | None) -> str:
    """Mappe un type CyberForge vers une clé PROJECT_ANALYZERS."""
    raw = (project_type or "website").strip().lower()
    return CYBERFORGE_PROJECT_TYPE_MAP.get(raw, raw)


def openhands_eligible(
    *,
    plan: _OpenHandsPlan,
    generation_mode: str | None,
    enabled: bool = True,
    threshold: int = 7,
) -> bool:
    """Projets real_app ou application_web avec complexité ≥ seuil."""
    if not enabled:
        return False
    if plan.complexity_score < threshold:
        return False
    mode = (generation_mode or "client_demo").strip()
    if mode == "real_app":
        return True
    return plan.project_type == ProjectType.APPLICATION_WEB


class OpenHandsAgent(BaseAgent):
    """
    Agent d'analyse et de correction automatique.
    Fonctionne via l'API REST OpenHands Cloud.
    Fallback local si pas de clé API configurée.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings)
        self.api_key = plain_secret_str(self._settings.openhands_api_key)
        self.api_url = (self._settings.openhands_api_url or DEFAULT_OPENHANDS_API_URL).rstrip("/")
        self.has_api = bool(self.api_key)

    @property
    def agent_id(self) -> str:
        return "openhands"

    @property
    def name(self) -> str:
        return "OpenHands"

    def is_configured(self) -> bool:
        return self.has_api

    async def run(self, prompt: str, **kwargs: Any) -> str:
        code = str(kwargs.get("code") or prompt or "")
        project_type = normalize_project_type(kwargs.get("project_type"))
        project_name = str(kwargs.get("project_name") or "")
        iteration = int(kwargs.get("iteration") or 1)
        result = await self.analyze_and_fix(
            code,
            project_type,
            project_name=project_name,
            iteration=iteration,
        )
        return json.dumps(result, ensure_ascii=False)

    async def analyze_and_fix(
        self,
        code: str,
        project_type: str,
        project_name: str = "",
        iteration: int = 1,
    ) -> dict[str, Any]:
        """
        Analyse le code et retourne les corrections.
        Retourne toujours un dict structuré même en cas d'erreur.
        """
        normalized_type = normalize_project_type(project_type)
        analyzer_type = PROJECT_ANALYZERS.get(normalized_type, "web")
        rules = ANALYSIS_RULES.get(analyzer_type, ANALYSIS_RULES["web"])

        if self.has_api:
            return await self._analyze_via_api(
                code, normalized_type, project_name, rules, iteration
            )
        return await self._analyze_local(code, normalized_type, rules, iteration)

    async def run_correction_loop(
        self,
        code: str,
        *,
        project_type: str,
        project_name: str = "",
        context: SharedContext | None = None,
    ) -> tuple[str, SharedContext]:
        """
        Boucle d'auto-correction (pipeline) — met à jour SharedContext à chaque itération.
        """
        ctx = context or SharedContext()
        if not ctx.openhands_enabled:
            ctx.openhands_status = "skipped"
            return code, ctx

        ctx.openhands_status = "analyzing"
        current_code = code
        ctx.openhands_quality_before = float(ctx.openhands_quality_before or 0.0)

        max_iters = max(1, int(ctx.openhands_max_iterations or 3))
        all_issues: list[Any] = []
        all_corrections: list[Any] = []

        for i in range(1, max_iters + 1):
            ctx.openhands_iterations = i
            ctx.openhands_status = "correcting"
            result = await self.analyze_and_fix(
                current_code,
                project_type,
                project_name=project_name,
                iteration=i,
            )
            issues = list(result.get("issues_found") or [])
            corrections = list(result.get("corrections_applied") or [])
            all_issues.extend(issues)
            all_corrections.extend(corrections)
            current_code = str(result.get("corrected_code") or current_code)
            ctx.openhands_quality_after = float(result.get("quality_score") or 0.0)

            if not issues and not corrections:
                break

        ctx.openhands_issues_found = all_issues
        ctx.openhands_corrections_applied = all_corrections
        ctx.openhands_status = "done"
        ctx.openhands_report = {
            "project_type": normalize_project_type(project_type),
            "project_name": project_name,
            "iterations": ctx.openhands_iterations,
            "quality_before": ctx.openhands_quality_before,
            "quality_after": ctx.openhands_quality_after,
            "issues_count": len(all_issues),
            "corrections_count": len(all_corrections),
        }
        return current_code, ctx

    async def _analyze_via_api(
        self,
        code: str,
        project_type: str,
        project_name: str,
        rules: list[str],
        iteration: int,
    ) -> dict[str, Any]:
        """Analyse via OpenHands Cloud API REST."""
        rules_text = "\n".join(f"- {r}" for r in rules)
        task = f"""Tu es un expert en qualité de code pour des projets {project_type}.
Analyse ce code et corrige TOUS les problèmes trouvés.

RÈGLES D'ANALYSE :
{rules_text}

INSTRUCTIONS :
1. Identifie chaque problème avec sa localisation précise
2. Corrige chaque problème directement dans le code
3. Retourne UNIQUEMENT un JSON valide avec cette structure :
{{
    "issues_found": ["description problème 1", "description problème 2"],
    "corrections_applied": ["correction 1 appliquée", "correction 2 appliquée"],
    "corrected_code": "LE CODE COMPLET CORRIGÉ ICI",
    "quality_score": 85,
    "summary": "Résumé des corrections en 1 phrase"
}}

CODE À ANALYSER :
{code[:MAX_CODE_CHARS]}"""

        timeout = float(self._settings.openhands_timeout_seconds or 120.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_url}/app-conversations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "initial_message": {
                            "content": [{"type": "text", "text": task}]
                        }
                    },
                )
                response.raise_for_status()
                data = response.json()
                conversation_id = data.get("app_conversation_id")

                if not conversation_id:
                    logger.warning("OpenHands: pas de conversation_id, fallback local")
                    return await self._analyze_local(code, project_type, rules, iteration)

                result_text = await self._poll_conversation(client, str(conversation_id))
                return self._parse_result(result_text, code, iteration)

        except Exception as exc:
            logger.error("OpenHands API error: %s — fallback local", exc)
            return await self._analyze_local(code, project_type, rules, iteration)

    async def _poll_conversation(
        self,
        client: httpx.AsyncClient,
        conversation_id: str,
        max_wait: int = 90,
    ) -> str:
        """Polling du statut de la conversation OpenHands."""
        for _ in range(max_wait // 3):
            await asyncio.sleep(3)
            try:
                resp = await client.get(
                    f"{self.api_url}/app-conversations/{conversation_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                data = resp.json()
                status = str(data.get("status") or "")

                if status in ("READY", "COMPLETED", "done"):
                    messages = data.get("messages", [])
                    if isinstance(messages, list):
                        for msg in reversed(messages):
                            if not isinstance(msg, dict):
                                continue
                            if msg.get("role") != "assistant":
                                continue
                            content = msg.get("content", [])
                            if not isinstance(content, list):
                                continue
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    return str(block.get("text") or "")
                    return ""

                if status in ("ERROR", "FAILED"):
                    logger.warning("OpenHands conversation failed: %s", data)
                    return ""

            except Exception as exc:
                logger.warning("OpenHands polling error: %s", exc)
                continue

        return ""

    async def _analyze_local(
        self,
        code: str,
        project_type: str,
        rules: list[str],
        iteration: int,
    ) -> dict[str, Any]:
        """
        Fallback local : analyse statique sans API externe.
        Détecte les patterns d'erreurs les plus courants.
        """
        _ = rules
        issues: list[str] = []
        corrections: list[str] = []
        corrected_code = code

        analyzer_type = PROJECT_ANALYZERS.get(project_type, "web")

        if analyzer_type == "web":
            if "<!DOCTYPE html>" not in code and "<!doctype html>" not in code.lower():
                issues.append("DOCTYPE manquant")
                corrected_code = "<!DOCTYPE html>\n" + corrected_code
                corrections.append("DOCTYPE html ajouté")

            if 'href=""' in code or "href=''" in code:
                issues.append("Liens href vides détectés")
                corrected_code = corrected_code.replace('href=""', 'href="#"').replace(
                    "href=''", "href='#'"
                )
                corrections.append("Liens href vides remplacés par #")

            if "console.log(" in code:
                issues.append("console.log présents en production")
                corrected_code = re.sub(r"console\.log\([^)]*\);?\n?", "", corrected_code)
                corrections.append("console.log supprimés")

            if 'meta name="viewport"' not in code:
                issues.append("Meta viewport manquant")
                corrected_code = corrected_code.replace(
                    "<head>",
                    '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                )
                corrections.append("Meta viewport ajouté")

        elif analyzer_type == "electron":
            if "nodeIntegration: true" in code:
                issues.append("nodeIntegration true — faille de sécurité critique")
                corrected_code = corrected_code.replace(
                    "nodeIntegration: true", "nodeIntegration: false"
                )
                corrections.append("nodeIntegration forcé à false")

            if "contextIsolation: false" in code:
                issues.append("contextIsolation false — faille de sécurité")
                corrected_code = corrected_code.replace(
                    "contextIsolation: false", "contextIsolation: true"
                )
                corrections.append("contextIsolation forcé à true")

        elif analyzer_type == "mobile":
            if "<div" in code or "<span" in code:
                issues.append("Composants HTML web détectés dans fichier React Native")
                corrected_code = corrected_code.replace("<div", "<View").replace(
                    "</div>", "</View>"
                )
                corrected_code = corrected_code.replace("<span", "<Text").replace(
                    "</span>", "</Text>"
                )
                corrections.append("div→View, span→Text convertis")

        quality_score = max(0, 100 - (len(issues) * 10))

        return {
            "issues_found": issues,
            "corrections_applied": corrections,
            "corrected_code": corrected_code,
            "quality_score": quality_score,
            "summary": (
                f"Itération {iteration} — {len(issues)} problème(s) détecté(s), "
                f"{len(corrections)} correction(s) appliquée(s)"
            ),
            "source": "local_fallback",
            "iteration": iteration,
        }

    def _parse_result(self, text: str, original_code: str, iteration: int) -> dict[str, Any]:
        """Parse la réponse JSON d'OpenHands."""
        try:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, dict):
                    data["source"] = "openhands_api"
                    data["iteration"] = iteration
                    return data
        except Exception as exc:
            logger.warning("OpenHands parse error: %s", exc)

        return {
            "issues_found": [],
            "corrections_applied": [],
            "corrected_code": original_code,
            "quality_score": 75,
            "summary": f"Itération {iteration} — analyse complétée",
            "source": "openhands_api_raw",
            "iteration": iteration,
        }


openhands_agent = OpenHandsAgent()
