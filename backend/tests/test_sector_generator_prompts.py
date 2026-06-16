"""Tests instructions GeneratorAI par secteur."""

from __future__ import annotations

from agents.sector_generator_prompts import (
    APP_WEB_APPENDIX,
    CRM_APPENDIX,
    SECTOR_GENERATOR_PROFILES,
    _brief_kind,
    build_sector_generator_appendix,
    is_app_web_brief,
    is_crm_brief,
    resolve_sector_generator_profile,
)


def test_all_catalogued_sectors_have_profiles() -> None:
    expected_ids = {
        "artisan-btp",
        "restaurant-cafe",
        "sante-bien-etre",
        "nautique-marine",
        "immobilier-architecture",
        "beaute-coiffure",
        "formation-coaching",
        "garage-auto",
        "tourisme-loisirs",
        "camping-plein-air",
        "hotel-hebergement",
        "gite-location",
        "restaurant-table",
        "spa-bien-etre-resa",
        "activites-loisirs",
        "location-nautique",
        "mode-vetements",
        "artisan-createur",
        "bio-alimentation",
        "hightech-electronique",
        "maison-deco",
        "fleurs-cadeaux",
        "dashboard-analytics",
        "crm-clients",
        "crm-immobilier",
        "crm-recrutement",
        "crm-agence",
        "crm-coach",
        "planning-rdv",
        "gestion-entreprise",
        "stock-inventaire",
    }
    profile_ids = {p.id for p in SECTOR_GENERATOR_PROFILES}
    assert expected_ids == profile_ids


def test_vitrine_artisan_btp_profile() -> None:
    brief = {"project_type": "vitrine_next", "sector": "artisan / BTP"}
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "artisan-btp"
    appendix = build_sector_generator_appendix(brief)
    assert "Demander un devis" in appendix
    assert "Réalisations" in appendix


def test_reservation_camping_profile() -> None:
    brief = {"project_type": "site_reservation", "sector": "camping / plein air"}
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "camping-plein-air"
    appendix = build_sector_generator_appendix(brief)
    assert "Réserver mon séjour" in appendix


def test_ecommerce_mode_profile() -> None:
    brief = {"project_type": "ecommerce", "sector": "mode / vêtements"}
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "mode-vetements"
    appendix = build_sector_generator_appendix(brief)
    assert "Ajouter au panier" in appendix


def test_tourisme_loisirs_vitrine_profile() -> None:
    brief = {"project_type": "vitrine_next", "sector": "tourisme / loisirs"}
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "tourisme-loisirs"
    appendix = build_sector_generator_appendix(brief)
    assert "Hébergements" in appendix
    assert "Activités" in appendix


def test_vitrine_restaurant_label() -> None:
    brief = {"project_type": "vitrine_next", "sector": "Restaurant & Café"}
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "restaurant-cafe"


def test_sector_from_prompt_line() -> None:
    brief = {
        "project_type": "site_reservation",
        "prompt": "Client : Test\nSecteur : Hôtel & Hébergement\nDescription…",
    }
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "hotel-hebergement"


def test_application_web_brief_kind() -> None:
    brief = {"project_type": "application_web", "sector": "CRM / clients"}
    assert _brief_kind(brief) == "app_web"
    assert is_app_web_brief(brief)


def test_crm_brief_kind_and_profile() -> None:
    brief = {
        "project_type": "crm",
        "sector": "CRM / clients",
        "client_name": "CapCore CRM",
    }
    assert _brief_kind(brief) == "crm"
    assert is_crm_brief(brief)
    assert not is_app_web_brief(brief)
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "crm-clients"
    appendix = build_sector_generator_appendix(brief)
    assert "MODE CRM" in appendix
    assert "Pipeline Kanban" in appendix


def test_crm_appendix_has_required_ids() -> None:
    assert 'id="login-screen"' in CRM_APPENDIX
    assert 'id="view-pipeline"' in CRM_APPENDIX
    assert "demo2024" in CRM_APPENDIX


def test_app_web_appendix_has_required_ids() -> None:
    assert 'id="login-screen"' in APP_WEB_APPENDIX
    assert 'id="app-shell"' in APP_WEB_APPENDIX
    assert "demo2024" in APP_WEB_APPENDIX
    assert "#0f1117" in APP_WEB_APPENDIX
