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
from agents.architect_pricing import build_complexity_pricing
from tools.demo_template_service import (
    TEMPLATE_LABELS,
    VALID_TEMPLATES,
    detect_template_from_prompt,
)

logger = logging.getLogger(__name__)


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

        coremind = CoreMindAgent(self._settings)
        analysis = await coremind.analyze(normalized, project_type_hint)
        type_label = PROJECT_TYPE_LABELS[analysis.project_type]
        pricing = build_complexity_pricing(
            normalized,
            analysis.project_type,
            generation_mode=generation_mode,
        )

        llm_plan = await self._llm_refine(
            normalized,
            analysis,
            type_label,
            pricing=pricing,
        )
        if llm_plan is not None:
            return llm_plan, analysis

        template = detect_template_from_prompt(
            normalized,
            project_type_label=type_label,
        )
        template_label = TEMPLATE_LABELS.get(template, template)
        rationale = (
            f"Type « {type_label} » (complexité {pricing['complexity_label']} "
            f"{pricing['complexity_score']}/10). "
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
