"""
Démos client — templates premium préfabriqués (pas de génération HTML par LLM).

Le LLM choisit le template et personnalise les données seed (titre, marque, tâches).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace

from config import Settings, get_settings
from tools.codegen_service import (
    CodeGenService,
    CodeGenServiceError,
    CodeGenerateResult,
    GeneratedFile,
)
from tools.crm_template import MARKER as CRM_MARKER, TEMPLATE_ID as CRM_TEMPLATE_ID, build_html as build_crm_html
from tools.dashboard_template import (
    MARKER as DASHBOARD_MARKER,
    TEMPLATE_ID as DASHBOARD_TEMPLATE_ID,
    build_html as build_dashboard_html,
)
from tools.facturation_template import (
    MARKER as INVOICE_MARKER,
    TEMPLATE_ID as FACTURATION_TEMPLATE_ID,
    build_html as build_invoice_html,
)
from tools.landing_template import (
    MARKER as LANDING_MARKER,
    TEMPLATE_ID as LANDING_TEMPLATE_ID,
    build_html as build_landing_html,
)
from tools.premium_demo_data import (
    DEFAULT_PROFESSIONAL_TASKS,
    RESERVATION_SLOTS,
    RESERVATION_TASKS,
)
from tools.premium_seed_context import (
    contextual_crm_contacts,
    contextual_crm_pipeline,
    contextual_dashboard_chart,
    contextual_dashboard_kpis,
    contextual_dashboard_sectors,
    contextual_invoices,
    contextual_landing_features,
    contextual_landing_testimonials,
    contextual_reservation_bookings,
    contextual_tasks,
    detect_demo_vertical,
)
from tools.prompt_seed_hints import build_prompt_seed_hints, is_generic_brand
from tools.premium_reservation_html import RESERVATION_MARKER, build_premium_reservation_html
from tools.taskflow_template import (
    MARKER as TASKFLOW_MARKER,
    TEMPLATE_ID as TASKFLOW_TEMPLATE_ID,
    build_html as build_taskflow_html,
)

logger = logging.getLogger(__name__)

TEMPLATE_TASKFLOW = TASKFLOW_TEMPLATE_ID
TEMPLATE_LANDING = LANDING_TEMPLATE_ID
TEMPLATE_CRM = CRM_TEMPLATE_ID
TEMPLATE_DASHBOARD = DASHBOARD_TEMPLATE_ID
TEMPLATE_FACTURATION = FACTURATION_TEMPLATE_ID
TEMPLATE_INVOICE = TEMPLATE_FACTURATION  # alias rétrocompat
TEMPLATE_RESERVATION = "reservation"

VALID_TEMPLATES = frozenset(
    {
        TEMPLATE_TASKFLOW,
        TEMPLATE_LANDING,
        TEMPLATE_CRM,
        TEMPLATE_DASHBOARD,
        TEMPLATE_FACTURATION,
        "invoice",
        TEMPLATE_RESERVATION,
    }
)

TEMPLATE_MARKERS: dict[str, str] = {
    TEMPLATE_TASKFLOW: TASKFLOW_MARKER,
    TEMPLATE_LANDING: LANDING_MARKER,
    TEMPLATE_CRM: CRM_MARKER,
    TEMPLATE_DASHBOARD: DASHBOARD_MARKER,
    TEMPLATE_FACTURATION: INVOICE_MARKER,
    "invoice": INVOICE_MARKER,
    TEMPLATE_RESERVATION: RESERVATION_MARKER,
}

TEMPLATE_LABELS: dict[str, str] = {
    TEMPLATE_TASKFLOW: "TaskFlow",
    TEMPLATE_LANDING: "Landing page",
    TEMPLATE_CRM: "CRM",
    TEMPLATE_DASHBOARD: "Dashboard analytics",
    TEMPLATE_FACTURATION: "Facturation",
    TEMPLATE_RESERVATION: "Réservations",
}


def normalize_template_id(template: str) -> str:
    """Unifie les alias (invoice → facturation)."""
    t = (template or "").strip().lower()
    if t == "invoice":
        return TEMPLATE_FACTURATION
    if t in VALID_TEMPLATES:
        return t
    return TEMPLATE_TASKFLOW

TEMPLATE_PROVIDER = "cyberforge"
TEMPLATE_MODEL = "cyberforge-premium"

_DEFAULT_BRAND = "Studio Pro"
_DEFAULT_TAG = "Démo premium"
_DEFAULT_USER = "Alex Martin"
_DEFAULT_ROLE = "Utilisateur"

_DEFAULT_TASKS = DEFAULT_PROFESSIONAL_TASKS


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
    primary_color: str = ""
    secondary_color: str = ""
    logo_data_url: str = ""
    user_initials: str = ""
    stat_total: int | None = None
    stat_active: int | None = None
    stat_done: int | None = None
    context_prompt: str = ""
    project_type_label: str = ""


def detect_template_from_prompt(prompt: str, *, project_type_label: str = "") -> str:
    """Sélectionne le template premium selon le prompt et le type de projet."""
    blob = f"{project_type_label}\n{prompt}".lower()

    invoice_kw = (
        "facture",
        "facturation",
        "invoice",
        "tva",
        "devis",
        "billing",
        "comptabilité",
        "comptabilite",
    )
    crm_kw = (
        "crm",
        "contact",
        "contacts",
        "client",
        "clients",
        "pipeline",
        "commercial",
        "prospect",
        "opportunit",
        "vente",
        "sales",
    )
    dashboard_kw = (
        "dashboard",
        "analytics",
        "analytique",
        "kpi",
        "graphique",
        "statistique",
        "reporting",
        "tableau de bord",
        "metrics",
    )
    landing_kw = (
        "landing",
        "page d'accueil",
        "vitrine",
        "marketing",
        "hero",
        "présentation",
        "presentation",
        "site vitrine",
        "landing page",
    )
    reservation_kw = (
        "réservation",
        "reservation",
        "booking",
        "créneau",
        "creneau",
        "créneaux",
        "planning tables",
        "planning restaurant",
    )
    task_kw = (
        "tâche",
        "tache",
        "todo",
        "taskflow",
        "gestion de projet",
        "projet",
        "kanban",
    )

    scores: dict[str, int] = {
        TEMPLATE_FACTURATION: sum(1 for k in invoice_kw if k in blob),
        TEMPLATE_CRM: sum(1 for k in crm_kw if k in blob),
        TEMPLATE_DASHBOARD: sum(1 for k in dashboard_kw if k in blob),
        TEMPLATE_LANDING: sum(1 for k in landing_kw if k in blob),
        TEMPLATE_RESERVATION: sum(1 for k in reservation_kw if k in blob),
        TEMPLATE_TASKFLOW: sum(1 for k in task_kw if k in blob),
    }

    if re.search(r"\bcrm\b", blob, re.IGNORECASE):
        scores[TEMPLATE_CRM] += 8
    if re.search(
        r"\b(réservation|reservation|booking|créneau|creneau)\b",
        blob,
        re.IGNORECASE,
    ):
        scores[TEMPLATE_RESERVATION] += 8

    if "landing_page" in blob or "site_web" in blob:
        scores[TEMPLATE_LANDING] += 2
    if "saas_dashboard" in blob or "dashboard" in project_type_label.lower():
        scores[TEMPLATE_DASHBOARD] += 2
    if re.search(r"\b(dashboard|tableau de bord)\b", blob):
        scores[TEMPLATE_DASHBOARD] += 5

    specialized = max(
        scores[TEMPLATE_CRM],
        scores[TEMPLATE_DASHBOARD],
        scores[TEMPLATE_FACTURATION],
        scores[TEMPLATE_LANDING],
        scores[TEMPLATE_RESERVATION],
    )
    if "application_web" in blob and specialized == 0 and scores[TEMPLATE_LANDING] == 0:
        scores[TEMPLATE_TASKFLOW] += 1

    priority = (
        TEMPLATE_CRM,
        TEMPLATE_RESERVATION,
        TEMPLATE_FACTURATION,
        TEMPLATE_DASHBOARD,
        TEMPLATE_LANDING,
        TEMPLATE_TASKFLOW,
    )
    best = max(
        scores.items(),
        key=lambda x: (x[1], priority.index(x[0]) if x[0] in priority else 99),
    )
    if best[1] > 0:
        return best[0]
    return TEMPLATE_TASKFLOW


def align_seed_template(
    seed: DemoSeedData,
    prompt: str,
    *,
    project_type_label: str = "",
) -> DemoSeedData:
    """Le prompt utilisateur prime sur le champ template seed (ex. LLM → taskflow)."""
    detected = detect_template_from_prompt(
        prompt,
        project_type_label=project_type_label,
    )
    if seed.template == detected:
        return seed
    logger.info(
        "[DemoTemplate] template corrigé | seed=%s → détecté=%s",
        seed.template,
        detected,
    )
    return replace(
        seed,
        template=detected,
        subtitle=_subtitle_for_template(
            detected,
            seed.brand_name,
            prompt=seed.context_prompt or prompt,
            project_type_label=project_type_label,
        ),
        brand_tag=(
            seed.brand_tag
            if detected == TEMPLATE_TASKFLOW
            else f"{TEMPLATE_LABELS[detected]} Pro"
        ),
        tasks=_tasks_for_template(
            detected,
            seed.context_prompt or prompt,
            project_type_label=project_type_label or seed.project_type_label,
        ),
    )


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


def _brand_from_prompt(prompt: str, template: str) -> str:
    quoted = re.search(r"[«\"']([^«\"']{2,40})[»\"']", prompt)
    if quoted:
        return _clip(quoted.group(1), 32)
    lower = prompt.lower()
    if "agence marketing" in lower or (
        "agence" in lower and "marketing" in lower
    ):
        return _clip("Pulse Agency", 32)
    if "immobilier" in lower or "immobilière" in lower or "immobiliere" in lower:
        return _clip("Habitat Plus", 32)
    defaults = {
        TEMPLATE_LANDING: "NovaLaunch",
        TEMPLATE_CRM: "RelateCRM",
        TEMPLATE_DASHBOARD: "InsightHub",
        TEMPLATE_FACTURATION: "BillForge",
        TEMPLATE_RESERVATION: "BookTable",
        TEMPLATE_TASKFLOW: "TaskFlow",
    }
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
    ):
        if kw in prompt.lower():
            return _clip(kw.capitalize() + " Pro", 32)
    words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", prompt)
    if words:
        return _clip(words[0].capitalize(), 28)
    return defaults.get(template, _DEFAULT_BRAND)


def _subtitle_for_template(
    template: str,
    brand: str,
    *,
    prompt: str = "",
    project_type_label: str = "",
) -> str:
    vertical = detect_demo_vertical(
        f"{project_type_label}\n{prompt}",
        project_type_label=project_type_label,
    )
    if vertical == "marketing" and template == TEMPLATE_DASHBOARD:
        return (
            f"Campagnes, leads, ROI et clics — tableau de bord {brand} pour agences marketing."
        )
    if vertical == "marketing" and template == TEMPLATE_CRM:
        return f"Pipeline leads et comptes clients — {brand} pour équipes acquisition."
    if vertical == "real_estate" and template == TEMPLATE_CRM:
        return f"Mandats, visites et acheteurs — CRM {brand} pour l'immobilier."
    if vertical == "real_estate" and template == TEMPLATE_DASHBOARD:
        return f"Mandats, visites et commissions — pilotage {brand} en temps réel."
    subs = {
        TEMPLATE_LANDING: f"Découvrez {brand} — la plateforme qui convertit vos visiteurs en clients.",
        TEMPLATE_CRM: f"Pilotez votre pipeline commercial avec {brand}.",
        TEMPLATE_DASHBOARD: f"Visualisez vos KPIs en temps réel avec {brand}.",
        TEMPLATE_FACTURATION: f"Facturation simple et conforme avec {brand}.",
        TEMPLATE_RESERVATION: f"Gérez vos créneaux et tables avec {brand}.",
        TEMPLATE_TASKFLOW: f"Organisez votre travail avec {brand} — espace collaboratif premium.",
    }
    return subs.get(template, f"Démo interactive {brand}.")


_CRM_SEED_TASKS: tuple[tuple[str, bool], ...] = (
    ("Qualifier les nouveaux prospects du salon", False),
    ("Relancer les fiches en statut Prospect", False),
    ("Préparer la revue pipeline hebdomadaire", True),
    ("Mettre à jour les comptes clients actifs", False),
)

_DASHBOARD_SEED_TASKS: tuple[tuple[str, bool], ...] = (
    ("Consolider les KPIs du trimestre", False),
    ("Valider le graphique CA vs objectifs", False),
    ("Partager le rapport analytics à la direction", True),
    ("Configurer les alertes sur la marge", False),
)

_FACTURATION_SEED_TASKS: tuple[tuple[str, bool], ...] = (
    ("Relancer les factures en retard", False),
    ("Émettre les factures en attente de validation", False),
    ("Rapprocher les paiements du mois", True),
    ("Exporter le journal des ventes TVA", False),
)

_LANDING_SEED_TASKS: tuple[tuple[str, bool], ...] = (
    ("Finaliser le hero et le message principal", False),
    ("Ajuster les sections features et CTA", False),
    ("Publier la landing sur le domaine client", True),
    ("Configurer le suivi des conversions", False),
)


def _seed_context_blob(seed: DemoSeedData) -> str:
    return f"{seed.project_type_label}\n{seed.context_prompt or seed.title}"


def _vertical_for_seed(seed: DemoSeedData) -> str:
    return detect_demo_vertical(
        seed.context_prompt or seed.title,
        project_type_label=seed.project_type_label,
    )


def _tasks_for_template(
    template: str,
    prompt: str,
    *,
    project_type_label: str = "",
) -> tuple[tuple[str, bool], ...]:
    lower = prompt.lower()
    template = normalize_template_id(template)
    vertical = detect_demo_vertical(
        prompt,
        project_type_label=project_type_label,
    )
    contextual = contextual_tasks(
        template,
        vertical=vertical,
        prompt=prompt,
        project_type_label=project_type_label,
    )
    if contextual:
        return contextual
    if template == TEMPLATE_RESERVATION:
        return RESERVATION_TASKS
    if template == TEMPLATE_CRM:
        return _CRM_SEED_TASKS
    if template == TEMPLATE_DASHBOARD:
        return _DASHBOARD_SEED_TASKS
    if template == TEMPLATE_FACTURATION:
        return _FACTURATION_SEED_TASKS
    if template == TEMPLATE_LANDING:
        return _LANDING_SEED_TASKS
    if "restaurant" in lower or "café" in lower or "menu" in lower:
        return (
            ("Mettre à jour la carte des desserts", False),
            ("Confirmer les réservations du week-end", False),
            ("Commander les produits frais", True),
            ("Former l'équipe salle sur le POS", False),
        )
    return _DEFAULT_TASKS


def _tasks_from_prompt(
    prompt: str,
    *,
    project_type_label: str = "",
) -> tuple[tuple[str, bool], ...]:
    return _tasks_for_template(
        detect_template_from_prompt(prompt, project_type_label=project_type_label),
        prompt,
        project_type_label=project_type_label,
    )


def heuristic_demo_seed(prompt: str, *, project_type_label: str) -> DemoSeedData:
    """Personnalisation locale sans LLM."""
    clean = prompt.strip()
    template = detect_template_from_prompt(clean, project_type_label=project_type_label)
    title = _clip(clean.split("\n")[0] if clean else project_type_label, 72)
    if len(title) < 4:
        title = TEMPLATE_LABELS.get(template, "Démo client")
    brand = _brand_from_prompt(clean, template)
    vertical = detect_demo_vertical(clean, project_type_label=project_type_label)
    role = _DEFAULT_ROLE
    if vertical == "marketing":
        role = "Directrice marketing"
    elif vertical == "real_estate":
        role = "Agent immobilier senior"
    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_subtitle_for_template(
            template,
            brand,
            prompt=clean,
            project_type_label=project_type_label,
        ),
        brand_name=brand,
        brand_tag=_DEFAULT_TAG if template == TEMPLATE_TASKFLOW else f"{TEMPLATE_LABELS[template]} Pro",
        user_name=_DEFAULT_USER,
        user_role=role,
        tasks=_tasks_for_template(
            template,
            clean,
            project_type_label=project_type_label,
        ),
        llm_personalized=False,
        context_prompt=clean,
        project_type_label=project_type_label,
    )


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
        "primary_color": seed.primary_color,
        "secondary_color": seed.secondary_color,
        "logo_data_url": seed.logo_data_url,
        "user_initials": seed.user_initials,
        "stats": {
            "total": seed.stat_total,
            "active": seed.stat_active,
            "done": seed.stat_done,
        }
        if seed.stat_total is not None
        else None,
    }


def _normalize_logo_data_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    s = value.strip()
    if not s.startswith("data:image/"):
        return ""
    if "png" not in s[:30].lower() and "jpeg" not in s[:30].lower() and "jpg" not in s[:30].lower():
        return ""
    return s[:600_000]


def seed_from_dict(
    data: dict[str, object],
    *,
    prompt: str = "",
    project_type_label: str = "",
) -> DemoSeedData:
    title = _clip(str(data.get("title") or "Démo client"), 72)
    detected = detect_template_from_prompt(
        f"{prompt}\n{title}",
        project_type_label=project_type_label,
    )
    template = normalize_template_id(str(data.get("template") or ""))
    if template != detected:
        template = detected

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

    if len(tasks) < 3:
        tasks = list(
            _tasks_for_template(
                template,
                f"{prompt} {title}",
                project_type_label=project_type_label,
            )
        )

    stat_total: int | None = None
    stat_active: int | None = None
    stat_done: int | None = None
    stats_raw = data.get("stats")
    if isinstance(stats_raw, dict):
        try:
            if stats_raw.get("total") is not None:
                stat_total = max(0, int(stats_raw["total"]))
            if stats_raw.get("active") is not None:
                stat_active = max(0, int(stats_raw["active"]))
            if stats_raw.get("done") is not None:
                stat_done = max(0, int(stats_raw["done"]))
        except (TypeError, ValueError):
            pass

    user_name = _clip(str(data.get("user_name") or _DEFAULT_USER), 48)
    initials = _clip(str(data.get("user_initials") or ""), 8) or _initials(user_name)

    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_clip(
            str(
                data.get("subtitle")
                or _subtitle_for_template(
                    template,
                    str(data.get("brand_name") or title),
                    prompt=prompt,
                    project_type_label=project_type_label,
                )
            ),
            140,
        ),
        brand_name=_clip(str(data.get("brand_name") or _DEFAULT_BRAND), 40),
        brand_tag=_clip(str(data.get("brand_tag") or _DEFAULT_TAG), 48),
        user_name=user_name,
        user_role=_clip(str(data.get("user_role") or _DEFAULT_ROLE), 48),
        tasks=tuple(tasks),
        llm_personalized=bool(data.get("llm_personalized")),
        primary_color=_clip(str(data.get("primary_color") or ""), 16),
        secondary_color=_clip(str(data.get("secondary_color") or ""), 16),
        logo_data_url=_normalize_logo_data_url(data.get("logo_data_url")),
        user_initials=initials,
        stat_total=stat_total,
        stat_active=stat_active,
        stat_done=stat_done,
        context_prompt=prompt,
        project_type_label=project_type_label,
    )


def _reservation_bookings_from_seed(
    seed: DemoSeedData,
    *,
    vertical: str,
    hints: object,
) -> list[dict[str, str | int]]:
    prompt = seed.context_prompt or seed.title
    return contextual_reservation_bookings(
        vertical=vertical,
        brand_name=seed.brand_name,
        prompt=prompt,
        project_type_label=seed.project_type_label,
        hints=hints,  # type: ignore[arg-type]
    )


def enrich_demo_seed(seed: DemoSeedData) -> DemoSeedData:
    """
    Ré-applique prompt + type ArchitectAI pour forcer marque, tâches et métier cohérents.
    """
    prompt = (seed.context_prompt or seed.title).strip()
    label = seed.project_type_label or ""
    hints = build_prompt_seed_hints(prompt, project_type_label=label)
    template = normalize_template_id(seed.template)
    detected = detect_template_from_prompt(prompt, project_type_label=label)
    if detected != template:
        template = detected

    brand = seed.brand_name.strip()
    if is_generic_brand(brand) or brand == _DEFAULT_BRAND:
        brand = hints.brand_name

    tasks = contextual_tasks(
        template,
        vertical=hints.vertical,
        prompt=prompt,
        project_type_label=label,
        hints=hints,
    )
    if not tasks:
        tasks = _tasks_for_template(template, prompt, project_type_label=label)

    title = seed.title
    low_title = title.lower()
    if low_title in ("démo client", "démo cyberforge", "demo client") or len(title) < 5:
        first = _clip(prompt.split("\n")[0] if prompt else label, 72)
        if len(first) >= 4:
            title = first

    role = seed.user_role
    if role == _DEFAULT_ROLE:
        if hints.vertical == "marketing":
            role = "Directrice marketing"
        elif hints.vertical == "real_estate":
            role = "Agent immobilier senior"
        elif hints.vertical == "restaurant":
            role = "Chef / Gérant"

    subtitle = _subtitle_for_template(
        template,
        brand,
        prompt=prompt,
        project_type_label=label,
    )
    if (
        seed.llm_personalized
        and seed.subtitle
        and "cyberforge" not in seed.subtitle.lower()
        and hints.vertical == "generic"
    ):
        subtitle = seed.subtitle

    return replace(
        seed,
        template=template,
        title=title,
        subtitle=subtitle,
        brand_name=_clip(brand, 40),
        brand_tag=(
            seed.brand_tag
            if template == TEMPLATE_TASKFLOW
            else f"{TEMPLATE_LABELS.get(template, template)} Pro"
        ),
        user_role=_clip(role, 48),
        tasks=tuple(tasks),
        context_prompt=prompt,
        project_type_label=label,
    )


def build_html_from_seed(seed: DemoSeedData) -> str:
    """Assemble le HTML premium selon le template choisi."""
    seed = enrich_demo_seed(seed)
    prompt = seed.context_prompt or seed.title
    hints = build_prompt_seed_hints(prompt, project_type_label=seed.project_type_label)
    vertical = hints.vertical
    ctx = dict(
        vertical=vertical,
        prompt=prompt,
        project_type_label=seed.project_type_label,
        hints=hints,
    )
    common = dict(
        title=seed.title,
        subtitle=seed.subtitle,
        brand_name=seed.brand_name,
        brand_tag=seed.brand_tag,
        user_name=seed.user_name,
        user_role=seed.user_role,
    )
    tpl = normalize_template_id(seed.template)
    if tpl == TEMPLATE_CRM:
        return build_crm_html(
            **common,
            contacts=contextual_crm_contacts(
                brand_name=seed.brand_name,
                **ctx,
            ),
            pipeline=contextual_crm_pipeline(**ctx),
        )
    if tpl == TEMPLATE_DASHBOARD:
        return build_dashboard_html(
            **common,
            kpis=contextual_dashboard_kpis(**ctx),
            chart_bars=contextual_dashboard_chart(vertical=vertical),
            sectors=contextual_dashboard_sectors(**ctx),
        )
    if tpl == TEMPLATE_FACTURATION:
        return build_invoice_html(
            **common,
            invoices=contextual_invoices(brand_name=seed.brand_name, **ctx),
        )
    if tpl == TEMPLATE_RESERVATION:
        return build_premium_reservation_html(
            **common,
            bookings=_reservation_bookings_from_seed(seed, vertical=vertical, hints=hints),
        )
    if tpl == TEMPLATE_LANDING:
        return build_landing_html(
            **common,
            features=contextual_landing_features(**ctx),
            testimonials=contextual_landing_testimonials(vertical=vertical),
        )
    return build_taskflow_html(
        **common,
        user_initials=seed.user_initials or _initials(seed.user_name),
        seed_tasks=seed.tasks,
        primary_color=seed.primary_color or None,
        secondary_color=seed.secondary_color or None,
        logo_data_url=seed.logo_data_url or None,
        stat_total=seed.stat_total,
        stat_active=seed.stat_active,
        stat_done=seed.stat_done,
    )


def is_valid_demo_html(html: str, template: str) -> bool:
    marker = TEMPLATE_MARKERS.get(normalize_template_id(template), TASKFLOW_MARKER)
    return marker in html and len(html) > 800


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
        template_hint: str | None = None,
    ) -> DemoSeedData:
        seed = heuristic_demo_seed(prompt, project_type_label=project_type_label)
        if template_hint:
            hinted = normalize_template_id(template_hint)
            if seed.template != hinted:
                seed = replace(
                    seed,
                    template=hinted,
                    subtitle=_subtitle_for_template(
                        hinted,
                        seed.brand_name,
                        prompt=prompt,
                        project_type_label=project_type_label,
                    ),
                    brand_tag=(
                        seed.brand_tag
                        if hinted == TEMPLATE_TASKFLOW
                        else f"{TEMPLATE_LABELS[hinted]} Pro"
                    ),
                    tasks=_tasks_for_template(
                        hinted,
                        prompt,
                        project_type_label=project_type_label,
                    ),
                    context_prompt=prompt,
                    project_type_label=project_type_label,
                )
        codegen = CodeGenService(self._settings)
        if not codegen.is_configured():
            logger.info(
                "[DemoTemplate] seed heuristique | template=%s | title=%s",
                seed.template,
                seed.title,
            )
            return enrich_demo_seed(seed)
        try:
            data = await codegen.generate_demo_seed(
                prompt,
                project_type_label=project_type_label,
                template_hint=template_hint,
            )
            parsed = _parse_seed_payload(
                data,
                fallback_prompt=prompt,
                project_type_label=project_type_label,
            )
            parsed = replace(
                parsed,
                context_prompt=prompt,
                project_type_label=project_type_label,
                template=normalize_template_id(template_hint or parsed.template),
                tasks=_tasks_for_template(
                    normalize_template_id(template_hint or parsed.template),
                    prompt,
                    project_type_label=project_type_label,
                )
                if template_hint
                else parsed.tasks,
            )
            logger.info(
                "[DemoTemplate] seed LLM | template=%s | brand=%s",
                parsed.template,
                parsed.brand_name,
            )
            return enrich_demo_seed(parsed)
        except CodeGenServiceError as exc:
            logger.warning("[DemoTemplate] seed LLM échoué — heuristique : %s", exc)
            return enrich_demo_seed(seed)

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
        label = TEMPLATE_LABELS.get(seed.template, seed.template)
        summary = (
            f"Démo {seed.brand_name} — {label}"
            + (" (seed IA)" if seed.llm_personalized else "")
            + "."
        )
        logger.info(
            "[DemoTemplate] HTML | template=%s | bytes≈%s",
            seed.template,
            len(build_html_from_seed(seed).encode("utf-8")),
        )
        return seed_to_code_result(seed, summary=summary)


def _parse_seed_payload(
    data: dict,
    *,
    fallback_prompt: str = "",
    project_type_label: str = "",
) -> DemoSeedData:
    title = _clip(str(data.get("title") or "Démo client"), 72)
    template = normalize_template_id(
        str(data.get("template") or "")
    ) or detect_template_from_prompt(
        f"{fallback_prompt}\n{title}",
        project_type_label=project_type_label,
    )
    detected = detect_template_from_prompt(
        f"{fallback_prompt}\n{title}",
        project_type_label=project_type_label,
    )
    if template != detected:
        template = detected

    tasks_raw = data.get("tasks") or []
    tasks: list[tuple[str, bool]] = []
    if isinstance(tasks_raw, list):
        for item in tasks_raw[:8]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                tasks.append(
                    (
                        _clip(text, 140),
                        bool(
                            item.get("completed")
                            or item.get("done")
                            or item.get("checked")
                        ),
                    )
                )

    brand = _clip(str(data.get("brand_name") or _DEFAULT_BRAND), 40)
    if len(tasks) < 3:
        tasks = list(
            _tasks_for_template(
                template,
                f"{fallback_prompt} {title}",
                project_type_label=project_type_label,
            )
        )

    vertical = detect_demo_vertical(
        f"{fallback_prompt}\n{title}",
        project_type_label=project_type_label,
    )
    role = _clip(str(data.get("user_role") or _DEFAULT_ROLE), 48)
    if role == _DEFAULT_ROLE:
        if vertical == "marketing":
            role = "Directrice marketing"
        elif vertical == "real_estate":
            role = "Agent immobilier senior"

    return DemoSeedData(
        template=normalize_template_id(template),
        title=title,
        subtitle=_clip(
            str(
                data.get("subtitle")
                or _subtitle_for_template(
                    template,
                    brand,
                    prompt=fallback_prompt,
                    project_type_label=project_type_label,
                )
            ),
            140,
        ),
        brand_name=brand,
        brand_tag=_clip(
            str(data.get("brand_tag") or f"{TEMPLATE_LABELS[template]} Pro"),
            48,
        ),
        user_name=_clip(str(data.get("user_name") or _DEFAULT_USER), 48),
        user_role=role,
        tasks=tuple(tasks),
        llm_personalized=True,
        primary_color=_clip(str(data.get("primary_color") or ""), 16),
        logo_data_url=_normalize_logo_data_url(data.get("logo_data_url")),
        context_prompt=fallback_prompt,
        project_type_label=project_type_label,
    )
