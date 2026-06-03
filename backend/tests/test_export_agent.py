"""Tests ExportAI — routage fournisseur et manifeste."""

from agents.coremind_agent import ProjectType
from tools.deploy_manifest import (
    select_export_provider,
    slugify_project_name,
    unique_deploy_slug,
)


def test_select_cloudflare_for_landing() -> None:
    assert (
        select_export_provider(ProjectType.LANDING_PAGE, "landing page restaurant")
        == "cloudflare"
    )


def test_select_railway_for_api() -> None:
    assert (
        select_export_provider(ProjectType.API_BACKEND, "API REST FastAPI")
        == "railway"
    )


def test_slugify_project_name() -> None:
    assert slugify_project_name("Mon SaaS CRM!") == "mon-saas-crm"


def test_unique_deploy_slug_differs_per_call() -> None:
    a = unique_deploy_slug("mon-projet", project_id="gen-1")
    b = unique_deploy_slug("mon-projet", project_id="gen-2")
    assert a != b
    assert a.startswith("mon-projet-")
    assert len(a) <= 48
