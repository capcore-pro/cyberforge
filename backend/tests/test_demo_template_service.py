"""Tests démos template — HTML préfabriqué sans React."""

import asyncio
from unittest.mock import AsyncMock, patch

from tools.demo_template_service import (
    DemoTemplateService,
    build_html_from_seed,
    heuristic_demo_seed,
    seed_to_code_result,
)


def test_heuristic_seed_restaurant_tasks() -> None:
    seed = heuristic_demo_seed(
        "Site pour mon restaurant italien avec réservations",
        project_type_label="Site web",
    )
    assert seed.template == "taskflow"
    assert "restaurant" in seed.brand_name.lower() or "Restaurant" in seed.brand_name
    assert len(seed.tasks) >= 3


def test_build_html_taskflow_markers() -> None:
    seed = heuristic_demo_seed("App SaaS gestion de tâches", project_type_label="SaaS")
    html = build_html_from_seed(seed)
    assert "saas-shell" in html
    assert seed.brand_name in html
    assert "export default" not in html
    assert "import React" not in html


def test_build_client_demo_generation_no_html_llm() -> None:
    with patch.object(
        DemoTemplateService,
        "resolve_seed",
        new_callable=AsyncMock,
    ) as mock_seed:
        from tools.demo_template_service import DemoSeedData

        mock_seed.return_value = DemoSeedData(
            template="taskflow",
            title="Boulangerie Dupont",
            subtitle="Gérez vos commandes",
            brand_name="Boulangerie Dupont",
            brand_tag="Artisan",
            user_name="Marie Dupont",
            user_role="Gérante",
            tasks=(("Préparer les commandes du matin", False),),
        )
        result = asyncio.run(
            DemoTemplateService().build_client_demo_generation(
                user_prompt="boulangerie",
                project_type_label="Site web",
            )
        )
    assert result.model == "taskflow-premium"
    assert result.provider == "cyberforge"
    assert "saas-shell" in result.code
    assert not any(f.path.endswith(".tsx") for f in result.files)


def test_seed_to_code_result_index_html_only() -> None:
    seed = heuristic_demo_seed("Dashboard", project_type_label="SaaS")
    gen = seed_to_code_result(seed, summary="test")
    assert gen.files[0].path == "index.html"
    assert gen.files[0].content.startswith("<!DOCTYPE")
