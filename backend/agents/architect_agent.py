"""
ArchitectAI — analyse le prompt, choisit le type de projet et le template premium optimal.
Heuristiques par défaut ; Claude Haiku via langchain-anthropic si la clé est configurée.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.coremind_agent import (
    PROJECT_TYPE_LABELS,
    CoreMindAgent,
    CoreMindAnalysis,
    ProjectType,
)
from config import Settings, plain_secret_str
from agents.architect_pricing import (
    PricingCategory,
    build_complexity_pricing,
    resolve_pricing_category,
)
from tools.demo_template_service import (
    TEMPLATE_LABELS,
    VALID_TEMPLATES,
    detect_template_from_prompt,
)

logger = logging.getLogger(__name__)

_TYPE_PREFIX_RE = re.compile(
    r"^TYPE\s*:\s*([a-zA-Z0-9_-]+)\s*(?:\n([\s\S]*)|\s+([\s\S]*)|)$",
    re.IGNORECASE,
)

# Jeton TYPE: → (ProjectType, catégorie tarifaire optionnelle, generation_mode optionnel)
_FORCED_TYPE_ALIASES: dict[str, tuple[ProjectType, PricingCategory | None, str | None]] = {
    "vitrine_next": (ProjectType.SITE_WEB, "vitrine_next", "vitrine_next"),
    "site_reservation": (ProjectType.SITE_WEB, "site_reservation", None),
    "ecommerce": (ProjectType.APPLICATION_WEB, "ecommerce", None),
    "application_web": (ProjectType.APPLICATION_WEB, "application_web", "real_app"),
    "extension_navigateur": (
        ProjectType.EXTENSION_NAVIGATEUR,
        "extension_navigateur",
        None,
    ),
    "extension": (ProjectType.EXTENSION_NAVIGATEUR, "extension_navigateur", None),
    "application_desktop": (
        ProjectType.APPLICATION_DESKTOP,
        "application_desktop",
        None,
    ),
    "api_backend": (ProjectType.API_BACKEND, "application_web", None),
    "saas_dashboard": (ProjectType.SAAS_DASHBOARD, "application_web", None),
    "saas": (ProjectType.SAAS_DASHBOARD, "application_web", None),
    "landing_page": (ProjectType.LANDING_PAGE, "vitrine_next", None),
    "site_web": (ProjectType.SITE_WEB, "vitrine_next", None),
    "application_mobile": (ProjectType.APPLICATION_WEB, "application_web", None),
    "projet_generique": (ProjectType.PROJET_GENERIQUE, "application_web", None),
}


def parse_type_prefix(prompt: str) -> tuple[str | None, str]:
    """
    Extrait TYPE: <jeton> en tête de prompt.
    Retourne (jeton normalisé, corps du prompt sans la directive TYPE).
    """
    text = prompt.strip()
    if not text.upper().startswith("TYPE:"):
        return None, text

    match = _TYPE_PREFIX_RE.match(text)
    if not match:
        return None, text

    token = match.group(1).strip().lower().replace("-", "_")
    body = (match.group(2) or match.group(3) or "").strip()
    if not token:
        return None, text
    return token, body


def resolve_forced_type_token(token: str) -> tuple[ProjectType, PricingCategory | None, str | None]:
    """Interprète le jeton TYPE: (ProjectType, catégorie tarifaire, mode génération)."""
    key = token.strip().lower().replace("-", "_")
    if key in _FORCED_TYPE_ALIASES:
        return _FORCED_TYPE_ALIASES[key]
    try:
        project_type = ProjectType(key)
    except ValueError as exc:
        valid = sorted(
            set(_FORCED_TYPE_ALIASES.keys()) | {m.value for m in ProjectType}
        )
        raise ValueError(
            f"Type inconnu après TYPE: « {token} ». Valeurs acceptées : "
            + ", ".join(valid)
        ) from exc
    return project_type, None, None


class ArchitectPlan(BaseModel):
    """Plan d'architecture produit par ArchitectAI."""

    agent_id: str = "architect"
    agent_name: str = "ArchitectAI"
    project_type: ProjectType
    project_type_label: str
    template: str = Field(description="Identifiant template premium (taskflow, crm, …)")
    template_label: str
    rationale: str
    used_llm: bool = False
    complexity_score: int = Field(
        ge=1,
        le=10,
        description="Score de complexité prompt (1–10)",
    )
    complexity_label: str = Field(
        description='Libellé : "Simple", "Moyenne" ou "Complexe"',
    )
    market_price_min: int = Field(ge=0, description="Fourchette marché basse (€)")
    market_price_max: int = Field(ge=0, description="Fourchette marché haute (€)")
    suggested_price_min: int = Field(ge=0, description="Prix de vente suggéré bas (~40 % marché)")
    suggested_price_max: int = Field(ge=0, description="Prix de vente suggéré haut (~40 % marché)")
    pricing_category: str = Field(
        default="application_web",
        description="Catégorie tarifaire (vitrine_next, ecommerce, …)",
    )


class ArchitectAgent(BaseAgent):
    """Sélectionne type de projet + template avant la génération CoreMind."""

    @property
    def agent_id(self) -> str:
        return "architect"

    @property
    def name(self) -> str:
        return "ArchitectAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        hint = kwargs.get("project_type_hint")
        plan = await self.plan(prompt, project_type_hint=hint)
        return plan.model_dump_json()

    async def plan(
        self,
        prompt: str,
        *,
        project_type_hint: ProjectType | None = None,
        generation_mode: str | None = None,
    ) -> ArchitectPlan:
        """Analyse le prompt et retourne type + template."""
        plan, _ = await self.plan_with_analysis(
            prompt,
            project_type_hint=project_type_hint,
            generation_mode=generation_mode,
        )
        return plan

    async def plan_with_analysis(
        self,
        prompt: str,
        *,
        project_type_hint: ProjectType | None = None,
        generation_mode: str | None = None,
    ) -> tuple[ArchitectPlan, CoreMindAnalysis]:
        """Analyse le prompt et retourne le plan + l'analyse CoreMind."""
        normalized = prompt.strip()
        if len(normalized) < 3:
            raise ValueError("Le prompt ne peut pas être vide.")

        forced_token, body_prompt = parse_type_prefix(normalized)
        work_prompt = body_prompt if forced_token else normalized
        if forced_token and len(work_prompt) < 3:
            work_prompt = body_prompt or "Projet client"

        forced_category: PricingCategory | None = None
        effective_generation_mode = generation_mode
        forced_project_type: ProjectType | None = None

        if forced_token:
            forced_project_type, forced_category, forced_mode = resolve_forced_type_token(
                forced_token
            )
            if forced_mode:
                effective_generation_mode = forced_mode
            if forced_category is None:
                forced_category = resolve_pricing_category(
                    forced_project_type,
                    work_prompt,
                    generation_mode=effective_generation_mode,
                )

        coremind = CoreMindAgent(self._settings)
        type_hint = forced_project_type or project_type_hint
        analysis = await coremind.analyze(work_prompt, type_hint)
        type_label = PROJECT_TYPE_LABELS[analysis.project_type]
        pricing = build_complexity_pricing(
            work_prompt,
            analysis.project_type,
            generation_mode=effective_generation_mode,
            pricing_category=forced_category,
        )

        llm_plan = await self._llm_refine(
            work_prompt,
            analysis,
            type_label,
            pricing=pricing,
        )
        if llm_plan is not None:
            if forced_token:
                llm_plan = llm_plan.model_copy(
                    update={
                        "project_type": analysis.project_type,
                        "project_type_label": type_label,
                        "rationale": (
                            f"Type imposé (TYPE: {forced_token}) — {llm_plan.rationale}"
                        )[:500],
                        **self._pricing_fields(pricing),
                    }
                )
            return llm_plan, analysis

        template = detect_template_from_prompt(
            work_prompt,
            project_type_label=type_label,
        )
        template_label = TEMPLATE_LABELS.get(template, template)
        type_rationale = (
            f"Type imposé par TYPE: « {forced_token} » → « {type_label} ». "
            if forced_token
            else f"Type « {type_label} ». "
        )
        rationale = (
            f"{type_rationale}"
            f"Complexité {pricing['complexity_label']} {pricing['complexity_score']}/10. "
            f"Template premium « {template_label} » choisi par analyse heuristique du prompt. "
            f"Marché estimé {pricing['market_price_min']}–{pricing['market_price_max']} €."
        )
        plan = ArchitectPlan(
            project_type=analysis.project_type,
            project_type_label=type_label,
            template=template,
            template_label=template_label,
            rationale=rationale,
            used_llm=False,
            **pricing,
        )
        return plan, analysis

    @staticmethod
    def _pricing_fields(pricing: dict[str, int | str]) -> dict[str, int | str]:
        return {
            "complexity_score": int(pricing["complexity_score"]),
            "complexity_label": str(pricing["complexity_label"]),
            "market_price_min": int(pricing["market_price_min"]),
            "market_price_max": int(pricing["market_price_max"]),
            "suggested_price_min": int(pricing["suggested_price_min"]),
            "suggested_price_max": int(pricing["suggested_price_max"]),
            "pricing_category": str(pricing["pricing_category"]),
        }

    def _anthropic_key(self) -> str:
        raw = self._settings.anthropic_api_key
        return plain_secret_str(raw) if raw else ""

    async def _llm_refine(
        self,
        prompt: str,
        analysis: CoreMindAnalysis,
        type_label: str,
        *,
        pricing: dict[str, int | str],
    ) -> ArchitectPlan | None:
        api_key = self._anthropic_key()
        if not api_key:
            return None
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage, SystemMessage
        except ImportError:
            logger.debug("[ArchitectAI] langchain-anthropic indisponible")
            return None

        templates_list = ", ".join(sorted(VALID_TEMPLATES))
        system = (
            "Tu es ArchitectAI pour CyberForge. Réponds UNIQUEMENT en JSON valide, sans markdown.\n"
            f"Champs requis : template (un parmi {templates_list}), rationale (français, 1-2 phrases).\n"
            "Le project_type est déjà fixé par l'analyseur — ne le modifie pas."
        )
        user = (
            f"project_type_label: {type_label}\n"
            f"complexity: {analysis.complexity.value}\n"
            f"prompt:\n{prompt[:6000]}"
        )
        model_name = self._settings.coremind_haiku_model
        timeout = self._settings.coremind_llm_timeout_seconds
        try:
            llm = ChatAnthropic(
                model=model_name,
                api_key=api_key,
                timeout=timeout,
                max_tokens=512,
                temperature=0.2,
            )
            response = await llm.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=user)]
            )
            text = (response.content or "").strip()
            if isinstance(text, list):
                text = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in text
                )
            data = _parse_json_object(text)
            if not data:
                return None
            template = str(data.get("template") or "").strip().lower()
            if template not in VALID_TEMPLATES:
                template = detect_template_from_prompt(
                    prompt,
                    project_type_label=type_label,
                )
            rationale = str(data.get("rationale") or "").strip()
            if not rationale:
                rationale = (
                    f"Template « {TEMPLATE_LABELS.get(template, template)} » "
                    f"recommandé par ArchitectAI (Claude)."
                )
            return ArchitectPlan(
                project_type=analysis.project_type,
                project_type_label=type_label,
                template=template,
                template_label=TEMPLATE_LABELS.get(template, template),
                rationale=rationale[:500],
                used_llm=True,
                **self._pricing_fields(pricing),
            )
        except Exception:
            logger.warning("[ArchitectAI] appel LLM échoué — heuristique", exc_info=True)
            return None


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
