"""
CoreMindAI — orchestrateur central : analyse le prompt et recommande un outil.
Analyse heuristique (sans appel LLM) ; extensible via clés API configurées.
"""

from __future__ import annotations

import json
import logging
import re
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from security.llm_secrets import LLM_KEYS_UNAVAILABLE_MSG
from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    CodeGenServiceError,
    CodeGenerateResult,
    complexity_from_score,
)
from tools.demo_pipeline import build_client_demo_document
from tools.demo_template_service import TEMPLATE_MODEL, TEMPLATE_PROVIDER
from tools.pricing import estimate_cost_usd

logger = logging.getLogger(__name__)


class ProjectType(str, Enum):
    SITE_WEB = "site_web"
    LANDING_PAGE = "landing_page"
    APPLICATION_WEB = "application_web"
    APPLICATION_MOBILE = "application_mobile"
    EXTENSION_NAVIGATEUR = "extension_navigateur"
    API_BACKEND = "api_backend"
    APPLICATION_DESKTOP = "application_desktop"
    SAAS_DASHBOARD = "saas_dashboard"
    PROJET_GENERIQUE = "projet_generique"


class RecommendedTool(str, Enum):
    BOLT = "bolt.new"
    LOVABLE = "lovable"
    V0 = "v0"


class ComplexityLevel(str, Enum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    ELEVEE = "elevee"


PROJECT_TYPE_LABELS: dict[ProjectType, str] = {
    ProjectType.SITE_WEB: "Site web",
    ProjectType.LANDING_PAGE: "Landing page",
    ProjectType.APPLICATION_WEB: "Application web",
    ProjectType.APPLICATION_MOBILE: "Application mobile",
    ProjectType.EXTENSION_NAVIGATEUR: "Extension navigateur",
    ProjectType.API_BACKEND: "API / backend",
    ProjectType.APPLICATION_DESKTOP: "Application desktop",
    ProjectType.SAAS_DASHBOARD: "SaaS / tableau de bord",
    ProjectType.PROJET_GENERIQUE: "Projet générique",
}

# Mots-clés par type (français + anglais)
_TYPE_KEYWORDS: dict[ProjectType, tuple[str, ...]] = {
    ProjectType.LANDING_PAGE: (
        "landing page",
        "landing",
        "one page",
        "une page",
        "page unique",
        "hero",
        "cta",
    ),
    ProjectType.SITE_WEB: (
        "site web",
        "website",
        "portfolio",
        "vitrine",
        "page d'accueil",
        "homepage",
        "blog",
        "marketing",
        "multi-page",
    ),
    ProjectType.APPLICATION_WEB: (
        "application web",
        "web app",
        "spa",
        "react",
        "vue",
        "next.js",
        "nextjs",
        "fullstack",
        "full-stack",
    ),
    ProjectType.APPLICATION_MOBILE: (
        "mobile",
        "ios",
        "android",
        "react native",
        "flutter",
        "expo",
        "app store",
        "play store",
    ),
    ProjectType.EXTENSION_NAVIGATEUR: (
        "extension",
        "chrome extension",
        "firefox",
        "plugin navigateur",
        "browser extension",
        "addon",
    ),
    ProjectType.API_BACKEND: (
        "api",
        "backend",
        "rest",
        "graphql",
        "microservice",
        "fastapi",
        "endpoint",
        "webhook",
    ),
    ProjectType.APPLICATION_DESKTOP: (
        "desktop",
        "electron",
        "tauri",
        "application windows",
        "application mac",
        "logiciel",
    ),
    ProjectType.SAAS_DASHBOARD: (
        "saas",
        "dashboard",
        "tableau de bord",
        "admin panel",
        "backoffice",
        "crm",
        "analytics",
        "abonnement",
        "subscription",
    ),
}

_TOOL_BY_TYPE: dict[ProjectType, RecommendedTool] = {
    ProjectType.SITE_WEB: RecommendedTool.V0,
    ProjectType.LANDING_PAGE: RecommendedTool.V0,
    ProjectType.APPLICATION_WEB: RecommendedTool.LOVABLE,
    ProjectType.APPLICATION_MOBILE: RecommendedTool.BOLT,
    ProjectType.EXTENSION_NAVIGATEUR: RecommendedTool.BOLT,
    ProjectType.API_BACKEND: RecommendedTool.BOLT,
    ProjectType.APPLICATION_DESKTOP: RecommendedTool.BOLT,
    ProjectType.SAAS_DASHBOARD: RecommendedTool.LOVABLE,
    ProjectType.PROJET_GENERIQUE: RecommendedTool.LOVABLE,
}

_TOOL_RATIONALE: dict[RecommendedTool, str] = {
    RecommendedTool.V0: (
        "v0 excelle sur les interfaces React/Tailwind et les landings "
        "visuellement soignées avec itération rapide sur le design."
    ),
    RecommendedTool.LOVABLE: (
        "Lovable est adapté aux applications React complètes, aux flux "
        "multi-écrans et aux produits SaaS avec logique métier."
    ),
    RecommendedTool.BOLT: (
        "Bolt.new convient aux prototypes full-stack, backends, extensions "
        "et projets nécessitant une stack intégrée rapidement."
    ),
}

_COMPLEXITY_HIGH = (
    "authentification",
    "auth",
    "paiement",
    "payment",
    "stripe",
    "multi-tenant",
    "temps réel",
    "real-time",
    "websocket",
    "base de données",
    "database",
    "microservices",
    "kubernetes",
    "ci/cd",
    "internationalisation",
    "i18n",
)

_COMPLEXITY_LOW = (
    "mvp",
    "prototype",
    "simple",
    "landing",
    "one page",
    "une page",
    "statique",
    "vitrine",
    "poC",
    "poc",
)


class CoreMindAnalysis(BaseModel):
    """Résultat structuré de l'analyse CoreMindAI."""

    agent_id: str = "coremind"
    agent_name: str = "CoreMindAI"
    project_type: ProjectType
    project_type_label: str
    recommended_tool: RecommendedTool
    tool_rationale: str
    complexity: ComplexityLevel
    complexity_score: int = Field(ge=1, le=10)
    next_steps: list[str]
    summary: str


class GenerationMetrics(BaseModel):
    """Métriques affichées dans le Générateur."""

    model: str
    provider: str
    complexity: ComplexityLevel
    complexity_score: int = Field(ge=1, le=10)
    duration_ms: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    project_type_selected: str | None = None


class DemoPipelineSummary(BaseModel):
    """Métadonnées pipeline démo unique (template premium + seed)."""

    template: str = "taskflow"
    seed_personalized: bool = False
    html_bytes: int = 0
    single_file: str = "index.html"


class CoreMindRunResult(BaseModel):
    """Flow complet : analyse + sélection de modèles + génération."""

    analysis: CoreMindAnalysis
    generation: CodeGenerateResult
    metrics: GenerationMetrics
    planned_models: list[str] = Field(
        default_factory=list,
        description="Modèles configurés tentés par ordre de coût",
    )
    demo_pipeline: DemoPipelineSummary | None = None
    preview_html: str | None = Field(
        default=None,
        description="HTML premium unique (identique au fichier index.html livré)",
    )


class CoreMindAgent(BaseAgent):
    """Cerveau central — classification de projet et recommandation d'outil."""

    @property
    def agent_id(self) -> str:
        return "coremind"

    @property
    def name(self) -> str:
        return "CoreMindAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        analysis = await self.analyze(prompt)
        return analysis.model_dump_json()

    async def analyze(
        self,
        prompt: str,
        project_type_hint: ProjectType | None = None,
    ) -> CoreMindAnalysis:
        """Analyse un prompt utilisateur et retourne une recommandation structurée."""
        normalized = _normalize(prompt)
        if not normalized.strip():
            raise ValueError("Le prompt ne peut pas être vide.")

        project_type = project_type_hint or _detect_project_type(normalized)
        tool = _select_tool(normalized, project_type)
        complexity, score = _estimate_complexity(normalized)
        steps = _build_next_steps(project_type, tool, complexity)
        summary = _build_summary(
            normalized, project_type, tool, complexity, score
        )

        return CoreMindAnalysis(
            project_type=project_type,
            project_type_label=PROJECT_TYPE_LABELS[project_type],
            recommended_tool=tool,
            tool_rationale=_TOOL_RATIONALE[tool],
            complexity=complexity,
            complexity_score=score,
            next_steps=steps,
            summary=summary,
        )

    async def generate_code(self, prompt: str) -> CodeGenerateResult:
        """
        Génère du code via le routage CoreMindAI (coût croissant selon complexité).
        DeepSeek → Gemini Flash → Claude Haiku → Claude Sonnet si élevée.
        """
        normalized = _normalize(prompt)
        _, score = _estimate_complexity(normalized)
        tier = CodeGenComplexity(complexity_from_score(score).value)
        return await CodeGenService(self._settings).generate_code(prompt, tier)

    async def run_flow(
        self,
        prompt: str,
        project_type_hint: ProjectType | None = None,
    ) -> CoreMindRunResult:
        """Analyse le prompt puis assemble une démo client via template premium (pas de HTML LLM)."""
        analysis = await self.analyze(prompt, project_type_hint)
        tier = CodeGenComplexity(analysis.complexity.value)
        codegen = CodeGenService(self._settings)

        type_label = PROJECT_TYPE_LABELS.get(
            project_type_hint or analysis.project_type,
            analysis.project_type_label,
        )
        enriched = (
            f"Type de projet cible : {type_label}.\n\n{prompt.strip()}"
            if project_type_hint
            else prompt.strip()
        )

        start = time.perf_counter()
        document = await build_client_demo_document(
            enriched,
            project_type_label=type_label,
            settings=self._settings,
        )
        generation = document.generation
        preview_html = document.html
        pipeline_info = DemoPipelineSummary(
            template=document.seed.template,
            seed_personalized=document.seed.llm_personalized,
            html_bytes=document.html_bytes,
        )
        logger.info(
            "[CoreMindAI] DemoPipeline | template=%s | brand=%s | tasks=%s | "
            "preview_html_bytes=%s | seed_ia=%s",
            pipeline_info.template,
            document.seed.brand_name,
            len(document.seed.tasks),
            pipeline_info.html_bytes,
            pipeline_info.seed_personalized,
        )

        duration_ms = int((time.perf_counter() - start) * 1000)

        seed_input_chars = len(enriched) if codegen.is_configured() else 0
        output_chars = len(generation.code)
        cost = (
            estimate_cost_usd(
                generation.provider,
                generation.model,
                seed_input_chars,
                output_chars,
            )
            if generation.provider != TEMPLATE_PROVIDER
            else 0.0
        )

        planned = (
            codegen.planned_models(tier)
            if codegen.is_configured()
            else [f"{TEMPLATE_PROVIDER} · {TEMPLATE_MODEL} (template préfabriqué)"]
        )

        metrics = GenerationMetrics(
            model=generation.model,
            provider=generation.provider,
            complexity=analysis.complexity,
            complexity_score=analysis.complexity_score,
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
            project_type_selected=type_label if project_type_hint else None,
        )

        return CoreMindRunResult(
            analysis=analysis,
            generation=generation,
            metrics=metrics,
            planned_models=planned,
            demo_pipeline=pipeline_info,
            preview_html=preview_html,
        )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _detect_project_type(text: str) -> ProjectType:
    scores: dict[ProjectType, int] = {t: 0 for t in ProjectType}
    for project_type, keywords in _TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[project_type] += len(kw.split()) + 1

    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return ProjectType.PROJET_GENERIQUE


def _select_tool(text: str, project_type: ProjectType) -> RecommendedTool:
    """Affine l'outil selon des signaux UI/design dans le prompt."""
    ui_signals = (
        "design",
        "ui",
        "ux",
        "interface",
        "composant",
        "component",
        "shadcn",
        "tailwind",
        "figma",
    )
    fullstack_signals = ("fullstack", "full-stack", "backend", "api", "database")

    tool = _TOOL_BY_TYPE[project_type]

    if any(s in text for s in ui_signals) and project_type in (
        ProjectType.SITE_WEB,
        ProjectType.PROJET_GENERIQUE,
        ProjectType.APPLICATION_WEB,
    ):
        return RecommendedTool.V0

    if any(s in text for s in fullstack_signals) and project_type in (
        ProjectType.APPLICATION_WEB,
        ProjectType.SAAS_DASHBOARD,
        ProjectType.PROJET_GENERIQUE,
    ):
        return RecommendedTool.BOLT

    return tool


def _estimate_complexity(text: str) -> tuple[ComplexityLevel, int]:
    score = 4
    if len(text) > 200:
        score += 1
    if len(text) > 400:
        score += 1

    for kw in _COMPLEXITY_LOW:
        if kw in text:
            score -= 1
    for kw in _COMPLEXITY_HIGH:
        if kw in text:
            score += 2

    score = max(1, min(10, score))

    if score <= 3:
        return ComplexityLevel.FAIBLE, score
    if score <= 6:
        return ComplexityLevel.MOYENNE, score
    return ComplexityLevel.ELEVEE, score


def _build_next_steps(
    project_type: ProjectType,
    tool: RecommendedTool,
    complexity: ComplexityLevel,
) -> list[str]:
    steps = [
        f"Ouvrir {tool.value} et créer un nouveau projet aligné sur le type « {PROJECT_TYPE_LABELS[project_type]} ».",
        "Rédiger un brief initial reprenant les objectifs, contraintes et public cible du prompt.",
    ]

    if tool == RecommendedTool.V0:
        steps.append(
            "Itérer sur les maquettes UI (composants, palette néon/sombre) avant d'ajouter la logique."
        )
    elif tool == RecommendedTool.LOVABLE:
        steps.append(
            "Définir les écrans principaux et les flux utilisateur dans Lovable, puis connecter les données."
        )
    else:
        steps.append(
            "Générer le socle code via CoreMindAI (Claude), puis valider le schéma de données."
        )

    if complexity == ComplexityLevel.ELEVEE:
        steps.extend(
            [
                "Découper le projet en phases (auth, cœur métier, intégrations) avec jalons testables.",
                "Prévoir une revue sécurité (BugHunterAI) avant mise en production.",
            ]
        )
    elif complexity == ComplexityLevel.MOYENNE:
        steps.append(
            "Planifier un MVP testable en une itération, puis enrichir avec ArchitectAI."
        )
    else:
        steps.append(
            "Livrer un premier prototype fonctionnel, puis faire valider par TestPilotAI."
        )

    steps.append(
        "Exporter la documentation et les livrables via ExportAI une fois le socle validé."
    )
    return steps


def _build_summary(
    text: str,
    project_type: ProjectType,
    tool: RecommendedTool,
    complexity: ComplexityLevel,
    score: int,
) -> str:
    excerpt = text[:120] + ("…" if len(text) > 120 else "")
    return (
        f"CoreMindAI a classé la demande comme « {PROJECT_TYPE_LABELS[project_type]} » "
        f"(complexité {complexity.value}, score {score}/10). "
        f"Outil recommandé : {tool.value}. "
        f"Contexte analysé : « {excerpt} »"
    )
