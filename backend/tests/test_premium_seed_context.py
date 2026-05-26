"""Tests contextualisation secteur des démos premium."""

from tools.premium_seed_context import (
    contextual_dashboard_kpis,
    detect_demo_vertical,
)


def test_detect_marketing_vertical() -> None:
    assert (
        detect_demo_vertical(
            "Dashboard agence marketing campagnes leads ROI clics",
            project_type_label="SaaS",
        )
        == "marketing"
    )


def test_detect_real_estate_vertical() -> None:
    assert (
        detect_demo_vertical(
            "CRM immobilier mandats visites appartements",
            project_type_label="Application web",
        )
        == "real_estate"
    )


def test_marketing_dashboard_kpis() -> None:
    kpis = contextual_dashboard_kpis(vertical="marketing")
    labels = " ".join(k["label"].lower() for k in kpis)
    assert "lead" in labels or "campagne" in labels or "roi" in labels or "clic" in labels
