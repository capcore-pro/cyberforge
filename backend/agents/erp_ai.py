"""
Agent ERP AI — recommande l'ERP adapté selon le profil client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ErpType = Literal["odoo", "erpnext", "custom"]
CompanySize = Literal["solo", "small", "medium", "large"]
Budget = Literal["low", "medium", "high"]

ALL_MODULES = [
    "facturation",
    "stocks",
    "rh",
    "crm",
    "projets",
    "comptabilite",
]

MODULE_LABELS: dict[str, str] = {
    "facturation": "Facturation & devis",
    "stocks": "Gestion des stocks",
    "rh": "Gestion RH & employés",
    "crm": "Ventes & CRM",
    "projets": "Gestion de projets",
    "comptabilite": "Comptabilité complète",
}

ERP_LABELS: dict[str, str] = {
    "odoo": "Odoo 17",
    "erpnext": "ERPNext 15",
    "custom": "ERP Custom CapCore",
}

ERP_DESCRIPTIONS: dict[str, str] = {
    "odoo": (
        "Odoo est la solution la plus complète pour les structures exigeantes. "
        "Idéal pour une grande entreprise avec un budget conséquent et des besoins "
        "multi-départements."
    ),
    "erpnext": (
        "ERPNext offre un excellent équilibre entre puissance et simplicité. "
        "Parfait pour une PME ou une petite équipe qui veut un ERP professionnel "
        "sans la complexité d'Odoo."
    ),
    "custom": (
        "Notre ERP léger sur mesure : simple, rapide à déployer et économique. "
        "Idéal pour un auto-entrepreneur ou une petite structure avec un budget maîtrisé."
    ),
}

PRICING_ESTIMATES: dict[str, dict[str, int]] = {
    "custom": {"low": 1500, "medium": 2500, "high": 4000},
    "erpnext": {"low": 3000, "medium": 5500, "high": 8000},
    "odoo": {"low": 5000, "medium": 9000, "high": 15000},
}

ERP_MODULE_SUPPORT: dict[str, list[str]] = {
    "custom": ["facturation", "crm", "stocks"],
    "erpnext": ["facturation", "stocks", "rh", "crm", "projets", "comptabilite"],
    "odoo": ["facturation", "stocks", "rh", "crm", "projets", "comptabilite"],
}


@dataclass
class ErpRecommendation:
    erp_type: ErpType
    label: str
    description: str
    reason: str
    modules: list[str]
    module_labels: list[str]
    estimated_price_eur: int
    startup_guide: str
    alternatives: list[dict[str, str]]


def _normalize_modules(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(m) for m in raw if str(m) in ALL_MODULES]
    return []


def recommend_erp_type(
    company_size: str,
    budget: str,
    modules: list[str] | None = None,
) -> ErpType:
    """Logique de recommandation déterministe."""
    size = company_size if company_size in ("solo", "small", "medium", "large") else "small"
    bud = budget if budget in ("low", "medium", "high") else "medium"

    if size == "solo":
        return "custom"
    if size == "small" and bud == "low":
        return "custom"
    if size == "small" and bud == "medium":
        return "erpnext"
    if size == "medium":
        return "erpnext"
    if size == "large":
        return "odoo"
    if bud == "high":
        return "odoo"
    return "erpnext"


def _build_reason(erp_type: ErpType, company_size: str, budget: str) -> str:
    size_labels = {
        "solo": "auto-entrepreneur",
        "small": "petite équipe",
        "medium": "PME",
        "large": "grande entreprise",
    }
    budget_labels = {"low": "budget serré", "medium": "budget modéré", "high": "budget confortable"}
    return (
        f"Pour une {size_labels.get(company_size, 'structure')} avec un {budget_labels.get(budget, 'budget')}, "
        f"{ERP_LABELS[erp_type]} est le choix le plus adapté : bon rapport fonctionnalités / complexité / coût."
    )


def _startup_guide(erp_type: ErpType, modules: list[str]) -> str:
    mod_text = ", ".join(MODULE_LABELS.get(m, m) for m in modules[:4]) or "les modules de base"
    guides = {
        "custom": (
            f"1. Connectez-vous avec l'email admin fourni.\n"
            f"2. Activez {mod_text} depuis le tableau de bord.\n"
            f"3. Importez vos clients existants (CSV).\n"
            f"4. Créez votre premier devis en 2 clics."
        ),
        "erpnext": (
            f"1. Ouvrez l'URL et connectez-vous (Administrator).\n"
            f"2. Complétez l'assistant de configuration société.\n"
            f"3. Activez {mod_text} dans les modules.\n"
            f"4. Invitez votre équipe par email."
        ),
        "odoo": (
            f"1. Accédez à l'URL Odoo et connectez-vous.\n"
            f"2. Installez les applications : {mod_text}.\n"
            f"3. Configurez votre société et la TVA.\n"
            f"4. Formez 1 référent interne (30 min suffisent pour démarrer)."
        ),
    }
    return guides[erp_type]


def build_recommendation(project: dict[str, Any]) -> ErpRecommendation:
    """Construit la recommandation complète pour un projet."""
    company_size = str(project.get("company_size") or "small")
    budget = str(project.get("budget") or "medium")
    requested = _normalize_modules(project.get("modules"))

    erp_type = recommend_erp_type(company_size, budget)
    supported = ERP_MODULE_SUPPORT[erp_type]
    final_modules = [m for m in requested if m in supported] or supported[:3]

    price = PRICING_ESTIMATES[erp_type].get(budget, PRICING_ESTIMATES[erp_type]["medium"])

    alternatives: list[dict[str, str]] = []
    for alt in ("odoo", "erpnext", "custom"):
        if alt != erp_type:
            alternatives.append(
                {
                    "erp_type": alt,
                    "label": ERP_LABELS[alt],
                    "description": ERP_DESCRIPTIONS[alt][:120] + "…",
                }
            )

    return ErpRecommendation(
        erp_type=erp_type,
        label=ERP_LABELS[erp_type],
        description=ERP_DESCRIPTIONS[erp_type],
        reason=_build_reason(erp_type, company_size, budget),
        modules=final_modules,
        module_labels=[MODULE_LABELS[m] for m in final_modules],
        estimated_price_eur=price,
        startup_guide=_startup_guide(erp_type, final_modules),
        alternatives=alternatives,
    )


def recommendation_to_dict(rec: ErpRecommendation) -> dict[str, Any]:
    return {
        "erp_type": rec.erp_type,
        "label": rec.label,
        "description": rec.description,
        "reason": rec.reason,
        "modules": rec.modules,
        "module_labels": rec.module_labels,
        "estimated_price_eur": rec.estimated_price_eur,
        "startup_guide": rec.startup_guide,
        "alternatives": rec.alternatives,
    }
