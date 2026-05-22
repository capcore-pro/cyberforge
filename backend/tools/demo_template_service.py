"""
Démos client — templates premium préfabriqués (pas de génération HTML par LLM).

Le LLM ne choisit que le template et personnalise les données seed (titre, marque, tâches).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from config import Settings, get_settings
from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    CodeGenServiceError,
    CodeGenerateResult,
    GeneratedFile,
)
from tools.premium_task_saas_html import build_premium_task_manager_html

logger = logging.getLogger(__name__)

TEMPLATE_TASKFLOW = "taskflow"
TEMPLATE_PROVIDER = "cyberforge"
TEMPLATE_MODEL = "taskflow-premium"

_DEFAULT_BRAND = "TaskFlow"
_DEFAULT_TAG = "Workspace Pro"
_DEFAULT_USER = "Alex Martin"
_DEFAULT_ROLE = "Chef de projet"

_DEFAULT_TASKS: tuple[tuple[str, bool], ...] = (
    ("Finaliser la proposition client Acme Corp", False),
    ("Revoir le planning sprint Q2 avec l'équipe produit", False),
    ("Préparer la démo investisseurs (jeudi 14h)", True),
    ("Valider les maquettes onboarding mobile", False),
    ("Envoyer le compte-rendu réunion partenaires", False),
)


@dataclass(frozen=True)
class DemoSeedData:
    """Données injectées dans le template premium (jamais du HTML généré par LLM)."""

    template: str
    title: str
    subtitle: str
    brand_name: str
    brand_tag: str
    user_name: str
    user_role: str
    tasks: tuple[tuple[str, bool], ...]
    llm_personalized: bool = False


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "CF"


def _clip(text: str, max_len: int) -> str:
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _brand_from_prompt(prompt: str) -> str:
    quoted = re.search(r"[«\"']([^«\"']{2,40})[»\"']", prompt)
    if quoted:
        return _clip(quoted.group(1), 32)
    for kw in (
        "restaurant",
        "café",
        "boulangerie",
        "hôtel",
        "agence",
        "startup",
        "saas",
        "boutique",
        "clinique",
        "école",
    ):
        if kw in prompt.lower():
            return kw.capitalize() + " Pro"
    words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", prompt)
    if words:
        return _clip(words[0].capitalize(), 28)
    return _DEFAULT_BRAND


def seed_as_dict(seed: DemoSeedData) -> dict[str, object]:
    return {
        "template": seed.template,
        "title": seed.title,
        "subtitle": seed.subtitle,
        "brand_name": seed.brand_name,
        "brand_tag": seed.brand_tag,
        "user_name": seed.user_name,
        "user_role": seed.user_role,
        "tasks": [
            {"text": text, "completed": completed} for text, completed in seed.tasks
        ],
        "llm_personalized": seed.llm_personalized,
    }


def seed_from_dict(data: dict[str, object]) -> DemoSeedData:
    tasks_raw = data.get("tasks")
    tasks: list[tuple[str, bool]] = []
    if isinstance(tasks_raw, list):
        for item in tasks_raw:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            completed = bool(
                item.get("completed") or item.get("done") or item.get("checked")
            )
            tasks.append((_clip(text, 140), completed))
    if len(tasks) < 3:
        tasks = list(_tasks_from_prompt(str(data.get("title") or "")))
    return DemoSeedData(
        template=str(data.get("template") or TEMPLATE_TASKFLOW),
        title=_clip(str(data.get("title") or "Démo client"), 72),
        subtitle=_clip(str(data.get("subtitle") or ""), 140),
        brand_name=_clip(str(data.get("brand_name") or _DEFAULT_BRAND), 40),
        brand_tag=_clip(str(data.get("brand_tag") or _DEFAULT_TAG), 48),
        user_name=_clip(str(data.get("user_name") or _DEFAULT_USER), 48),
        user_role=_clip(str(data.get("user_role") or _DEFAULT_ROLE), 48),
        tasks=tuple(tasks) if tasks else _DEFAULT_TASKS,
        llm_personalized=bool(data.get("llm_personalized")),
    )


def _tasks_from_prompt(prompt: str) -> tuple[tuple[str, bool], ...]:
    lower = prompt.lower()
    if (
        "réservation" in lower
        or "reservation" in lower
        or "booking" in lower
        or "table" in lower
    ):
        return (
            ("Confirmer les réservations du vendredi soir", False),
            ("Mettre à jour le plan de salle (12 couverts)", False),
            ("Relancer les no-shows de la semaine dernière", True),
            ("Préparer le menu dégustation week-end", False),
            ("Synchroniser les créneaux OpenTable", False),
        )
    if "restaurant" in lower or "café" in lower or "menu" in lower:
        return (
            ("Mettre à jour la carte des desserts", False),
            ("Confirmer les réservations du week-end", False),
            ("Commander les produits frais (fournisseur BioMarché)", True),
            ("Former l'équipe salle sur le nouveau POS", False),
            ("Préparer la soirée événement vendredi", False),
        )
    if "immobilier" in lower or "agence" in lower:
        return (
            ("Relancer les leads visite appartement Marais", False),
            ("Signer le mandat exclusif rue de Rivoli", False),
            ("Préparer le dossier financement client Dubois", True),
            ("Publier les annonces neuf Q2", False),
        )
    if "e-commerce" in lower or "boutique" in lower or "shop" in lower:
        return (
            ("Lancer la campagne soldes printemps", False),
            ("Optimiser les fiches produits best-sellers", False),
            ("Traiter les retours SAV en attente", True),
            ("Synchroniser le stock entrepôt", False),
        )
    return _DEFAULT_TASKS


def heuristic_demo_seed(prompt: str, *, project_type_label: str) -> DemoSeedData:
    """Personnalisation locale sans LLM."""
    clean = prompt.strip()
    title = _clip(clean.split("\n")[0] if clean else project_type_label, 72)
    if len(title) < 4:
        title = project_type_label or "Démo client"
    brand = _brand_from_prompt(clean)
    subtitle = _clip(
        f"Espace de travail {brand} — démo interactive adaptée à votre projet.",
        120,
    )
    return DemoSeedData(
        template=TEMPLATE_TASKFLOW,
        title=title,
        subtitle=subtitle,
        brand_name=brand,
        brand_tag="Workspace Pro",
        user_name=_DEFAULT_USER,
        user_role=_DEFAULT_ROLE,
        tasks=_tasks_from_prompt(clean),
        llm_personalized=False,
    )


def _parse_seed_payload(data: dict) -> DemoSeedData:
    template = str(data.get("template") or TEMPLATE_TASKFLOW).strip().lower()
    if template != TEMPLATE_TASKFLOW:
        template = TEMPLATE_TASKFLOW

    tasks_raw = data.get("tasks") or []
    tasks: list[tuple[str, bool]] = []
    if isinstance(tasks_raw, list):
        for item in tasks_raw[:8]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            completed = bool(
                item.get("completed") or item.get("done") or item.get("checked")
            )
            tasks.append((_clip(text, 140), completed))
    title = _clip(str(data.get("title") or "Démo client"), 72)
    if len(tasks) < 3:
        tasks = list(_tasks_from_prompt(title))

    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_clip(
            str(data.get("subtitle") or "Planifiez et pilotez votre activité."),
            140,
        ),
        brand_name=_clip(str(data.get("brand_name") or _DEFAULT_BRAND), 40),
        brand_tag=_clip(str(data.get("brand_tag") or _DEFAULT_TAG), 48),
        user_name=_clip(str(data.get("user_name") or _DEFAULT_USER), 48),
        user_role=_clip(str(data.get("user_role") or _DEFAULT_ROLE), 48),
        tasks=tuple(tasks),
        llm_personalized=True,
    )


def build_html_from_seed(seed: DemoSeedData) -> str:
    """Assemble le HTML premium à partir du template TaskFlow."""
    return build_premium_task_manager_html(
        title=seed.title,
        subtitle=seed.subtitle,
        brand_name=seed.brand_name,
        brand_tag=seed.brand_tag,
        user_name=seed.user_name,
        user_role=seed.user_role,
        user_initials=_initials(seed.user_name),
        seed_tasks=seed.tasks,
    )


def seed_to_code_result(seed: DemoSeedData, *, summary: str) -> CodeGenerateResult:
    html = build_html_from_seed(seed)
    return CodeGenerateResult(
        summary=summary,
        code=html,
        files=[GeneratedFile(path="index.html", content=html)],
        stack=["html", "css", "javascript"],
        model=TEMPLATE_MODEL,
        provider=TEMPLATE_PROVIDER,
        demo_seed=seed_as_dict(seed),
    )


class DemoTemplateService:
    """Orchestre template + personnalisation seed (LLM optionnel)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def resolve_seed(
        self,
        prompt: str,
        *,
        project_type_label: str,
    ) -> DemoSeedData:
        seed = heuristic_demo_seed(prompt, project_type_label=project_type_label)
        codegen = CodeGenService(self._settings)
        if not codegen.is_configured():
            logger.info(
                "[DemoTemplate] LLM indisponible — seed heuristique | title=%s",
                seed.title,
            )
            return seed
        try:
            data = await codegen.generate_demo_seed(
                prompt,
                project_type_label=project_type_label,
            )
            parsed = _parse_seed_payload(data)
            logger.info(
                "[DemoTemplate] seed LLM | template=%s | brand=%s | tasks=%s",
                parsed.template,
                parsed.brand_name,
                len(parsed.tasks),
            )
            return parsed
        except CodeGenServiceError as exc:
            logger.warning("[DemoTemplate] seed LLM échoué — heuristique : %s", exc)
            return seed

    async def build_client_demo_generation(
        self,
        *,
        user_prompt: str,
        project_type_label: str,
        seed: DemoSeedData | None = None,
    ) -> CodeGenerateResult:
        if seed is None:
            seed = await self.resolve_seed(
                user_prompt,
                project_type_label=project_type_label,
            )
        summary = (
            f"Démo {seed.brand_name} — template TaskFlow premium"
            + (" (données personnalisées par IA)" if seed.llm_personalized else "")
            + "."
        )
        logger.info(
            "[DemoTemplate] HTML préfabriqué | template=%s | bytes≈%s",
            seed.template,
            len(build_html_from_seed(seed).encode("utf-8")),
        )
        return seed_to_code_result(seed, summary=summary)
