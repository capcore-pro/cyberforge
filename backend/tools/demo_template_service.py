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
from tools.premium_crm_html import CRM_MARKER, build_premium_crm_html
from tools.premium_dashboard_html import DASHBOARD_MARKER, build_premium_dashboard_html
from tools.premium_demo_data import (
    CRM_CONTACTS,
    CRM_PIPELINE,
    DASHBOARD_CHART,
    DASHBOARD_KPIS,
    DASHBOARD_SECTORS,
    DEFAULT_PROFESSIONAL_TASKS,
    INVOICES,
    LANDING_FEATURES,
    LANDING_TESTIMONIALS,
    RESERVATION_SLOTS,
    RESERVATION_TASKS,
)
from tools.premium_invoice_html import INVOICE_MARKER, build_premium_invoice_html
from tools.premium_landing_page_html import LANDING_MARKER, build_premium_landing_html
from tools.premium_reservation_html import RESERVATION_MARKER, build_premium_reservation_html
from tools.premium_task_saas_html import PREMIUM_PREVIEW_MARKER, build_premium_task_manager_html

logger = logging.getLogger(__name__)

TEMPLATE_TASKFLOW = "taskflow"
TEMPLATE_LANDING = "landing"
TEMPLATE_CRM = "crm"
TEMPLATE_DASHBOARD = "dashboard"
TEMPLATE_INVOICE = "invoice"
TEMPLATE_RESERVATION = "reservation"

VALID_TEMPLATES = frozenset(
    {
        TEMPLATE_TASKFLOW,
        TEMPLATE_LANDING,
        TEMPLATE_CRM,
        TEMPLATE_DASHBOARD,
        TEMPLATE_INVOICE,
        TEMPLATE_RESERVATION,
    }
)

TEMPLATE_MARKERS: dict[str, str] = {
    TEMPLATE_TASKFLOW: "saas-shell",
    TEMPLATE_LANDING: LANDING_MARKER,
    TEMPLATE_CRM: CRM_MARKER,
    TEMPLATE_DASHBOARD: DASHBOARD_MARKER,
    TEMPLATE_INVOICE: INVOICE_MARKER,
    TEMPLATE_RESERVATION: RESERVATION_MARKER,
}

TEMPLATE_LABELS: dict[str, str] = {
    TEMPLATE_TASKFLOW: "TaskFlow",
    TEMPLATE_LANDING: "Landing page",
    TEMPLATE_CRM: "CRM",
    TEMPLATE_DASHBOARD: "Dashboard analytics",
    TEMPLATE_INVOICE: "Facturation",
    TEMPLATE_RESERVATION: "Réservations",
}

TEMPLATE_PROVIDER = "cyberforge"
TEMPLATE_MODEL = "cyberforge-premium"

_DEFAULT_BRAND = "CyberForge"
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
    logo_data_url: str = ""


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
        TEMPLATE_INVOICE: sum(1 for k in invoice_kw if k in blob),
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

    specialized = max(
        scores[TEMPLATE_CRM],
        scores[TEMPLATE_DASHBOARD],
        scores[TEMPLATE_INVOICE],
        scores[TEMPLATE_LANDING],
        scores[TEMPLATE_RESERVATION],
    )
    if "application_web" in blob and specialized == 0 and scores[TEMPLATE_LANDING] == 0:
        scores[TEMPLATE_TASKFLOW] += 1

    priority = (
        TEMPLATE_CRM,
        TEMPLATE_RESERVATION,
        TEMPLATE_INVOICE,
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
        subtitle=_subtitle_for_template(detected, seed.brand_name),
        brand_tag=(
            seed.brand_tag
            if detected == TEMPLATE_TASKFLOW
            else f"{TEMPLATE_LABELS[detected]} Pro"
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
    defaults = {
        TEMPLATE_LANDING: "NovaLaunch",
        TEMPLATE_CRM: "RelateCRM",
        TEMPLATE_DASHBOARD: "InsightHub",
        TEMPLATE_INVOICE: "BillForge",
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


def _subtitle_for_template(template: str, brand: str) -> str:
    subs = {
        TEMPLATE_LANDING: f"Découvrez {brand} — la plateforme qui convertit vos visiteurs en clients.",
        TEMPLATE_CRM: f"Pilotez votre pipeline commercial avec {brand}.",
        TEMPLATE_DASHBOARD: f"Visualisez vos KPIs en temps réel avec {brand}.",
        TEMPLATE_INVOICE: f"Facturation simple et conforme avec {brand}.",
        TEMPLATE_RESERVATION: f"Gérez vos créneaux et tables avec {brand}.",
        TEMPLATE_TASKFLOW: f"Organisez votre travail avec {brand} — espace collaboratif premium.",
    }
    return subs.get(template, f"Démo interactive {brand}.")


def _tasks_from_prompt(prompt: str) -> tuple[tuple[str, bool], ...]:
    lower = prompt.lower()
    if detect_template_from_prompt(prompt) == TEMPLATE_RESERVATION:
        return RESERVATION_TASKS
    if "restaurant" in lower or "café" in lower or "menu" in lower:
        return (
            ("Mettre à jour la carte des desserts", False),
            ("Confirmer les réservations du week-end", False),
            ("Commander les produits frais", True),
            ("Former l'équipe salle sur le POS", False),
        )
    return _DEFAULT_TASKS


def heuristic_demo_seed(prompt: str, *, project_type_label: str) -> DemoSeedData:
    """Personnalisation locale sans LLM."""
    clean = prompt.strip()
    template = detect_template_from_prompt(clean, project_type_label=project_type_label)
    title = _clip(clean.split("\n")[0] if clean else project_type_label, 72)
    if len(title) < 4:
        title = TEMPLATE_LABELS.get(template, "Démo client")
    brand = _brand_from_prompt(clean, template)
    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_subtitle_for_template(template, brand),
        brand_name=brand,
        brand_tag=_DEFAULT_TAG if template == TEMPLATE_TASKFLOW else f"{TEMPLATE_LABELS[template]} Pro",
        user_name=_DEFAULT_USER,
        user_role=_DEFAULT_ROLE,
        tasks=_tasks_from_prompt(clean),
        llm_personalized=False,
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
        "logo_data_url": seed.logo_data_url,
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
    template = str(data.get("template") or "").strip().lower()
    if template not in VALID_TEMPLATES or template != detected:
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
        tasks = list(_tasks_from_prompt(f"{prompt} {title}"))

    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_clip(str(data.get("subtitle") or _subtitle_for_template(template, title)), 140),
        brand_name=_clip(str(data.get("brand_name") or _DEFAULT_BRAND), 40),
        brand_tag=_clip(str(data.get("brand_tag") or _DEFAULT_TAG), 48),
        user_name=_clip(str(data.get("user_name") or _DEFAULT_USER), 48),
        user_role=_clip(str(data.get("user_role") or _DEFAULT_ROLE), 48),
        tasks=tuple(tasks),
        llm_personalized=bool(data.get("llm_personalized")),
        primary_color=_clip(str(data.get("primary_color") or ""), 16),
        logo_data_url=_normalize_logo_data_url(data.get("logo_data_url")),
    )


def _crm_contacts_from_seed(seed: DemoSeedData) -> list[dict[str, str]]:
    """Contacts CRM fictifs (Jean Dupont, Marie Martin, entreprises, statuts pipeline)."""
    contacts = [dict(c) for c in CRM_CONTACTS]
    if contacts:
        contacts[0] = {**contacts[0], "company": seed.brand_name}
    return contacts


def _reservation_bookings_from_seed(seed: DemoSeedData) -> list[dict[str, str | int]]:
    return [dict(b) for b in RESERVATION_SLOTS]


def build_html_from_seed(seed: DemoSeedData) -> str:
    """Assemble le HTML premium selon le template choisi."""
    common = dict(
        title=seed.title,
        subtitle=seed.subtitle,
        brand_name=seed.brand_name,
        brand_tag=seed.brand_tag,
        user_name=seed.user_name,
        user_role=seed.user_role,
    )
    if seed.template == TEMPLATE_CRM:
        return build_premium_crm_html(
            **common,
            contacts=_crm_contacts_from_seed(seed),
            pipeline=[dict(p) for p in CRM_PIPELINE],
        )
    if seed.template == TEMPLATE_DASHBOARD:
        return build_premium_dashboard_html(
            **common,
            kpis=[dict(k) for k in DASHBOARD_KPIS],
            chart_bars=[dict(b) for b in DASHBOARD_CHART],
            sectors=[dict(s) for s in DASHBOARD_SECTORS],
        )
    if seed.template == TEMPLATE_INVOICE:
        return build_premium_invoice_html(
            **common,
            invoices=[dict(i) for i in INVOICES],
        )
    if seed.template == TEMPLATE_RESERVATION:
        return build_premium_reservation_html(
            **common,
            bookings=_reservation_bookings_from_seed(seed),
        )
    if seed.template == TEMPLATE_LANDING:
        return build_premium_landing_html(
            **common,
            features=LANDING_FEATURES,
            testimonials=[dict(t) for t in LANDING_TESTIMONIALS],
        )
    return build_premium_task_manager_html(
        **common,
        user_initials=_initials(seed.user_name),
        seed_tasks=seed.tasks,
        primary_color=seed.primary_color or None,
        logo_data_url=seed.logo_data_url or None,
    )


def is_valid_demo_html(html: str, template: str) -> bool:
    marker = TEMPLATE_MARKERS.get(template, "saas-shell")
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
    ) -> DemoSeedData:
        seed = heuristic_demo_seed(prompt, project_type_label=project_type_label)
        codegen = CodeGenService(self._settings)
        if not codegen.is_configured():
            logger.info(
                "[DemoTemplate] seed heuristique | template=%s | title=%s",
                seed.template,
                seed.title,
            )
            return seed
        try:
            data = await codegen.generate_demo_seed(
                prompt,
                project_type_label=project_type_label,
            )
            parsed = _parse_seed_payload(data, fallback_prompt=prompt)
            logger.info(
                "[DemoTemplate] seed LLM | template=%s | brand=%s",
                parsed.template,
                parsed.brand_name,
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
    template = detect_template_from_prompt(
        f"{fallback_prompt}\n{title}",
        project_type_label=project_type_label,
    )

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
        tasks = list(_tasks_from_prompt(f"{fallback_prompt} {title}"))

    return DemoSeedData(
        template=template,
        title=title,
        subtitle=_clip(
            str(data.get("subtitle") or _subtitle_for_template(template, brand)),
            140,
        ),
        brand_name=brand,
        brand_tag=_clip(
            str(data.get("brand_tag") or f"{TEMPLATE_LABELS[template]} Pro"),
            48,
        ),
        user_name=_clip(str(data.get("user_name") or _DEFAULT_USER), 48),
        user_role=_clip(str(data.get("user_role") or _DEFAULT_ROLE), 48),
        tasks=tuple(tasks),
        llm_personalized=True,
        primary_color=_clip(str(data.get("primary_color") or ""), 16),
        logo_data_url=_normalize_logo_data_url(data.get("logo_data_url")),
    )
