"""Tests des 5 templates premium + gate mot de passe."""

from tools.crm_template import build_gated_crm_html
from tools.dashboard_template import build_gated_dashboard_html
from tools.facturation_template import build_gated_facturation_html
from tools.landing_template import build_gated_landing_html
from tools.taskflow_template import build_gated_taskflow_html


def test_all_templates_support_password_gate() -> None:
    builders = (
        (build_gated_taskflow_html, {"brand_name": "TaskFlow"}),
        (build_gated_crm_html, {"brand_name": "RelateCRM"}),
        (build_gated_dashboard_html, {"brand_name": "InsightHub"}),
        (build_gated_landing_html, {"brand_name": "NovaLaunch"}),
        (build_gated_facturation_html, {"brand_name": "BillForge"}),
    )
    for build_gated, kwargs in builders:
        html = build_gated("demo-secret", title="Test", **kwargs)
        assert "cf-password-toggle" in html
        assert "viewport" in html
