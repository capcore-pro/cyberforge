"""Priorité HTML upload Cloudflare (assembled_html > preview_html > generation)."""

from tools.codegen_service import CodeGenerateResult, GeneratedFile
from tools.export_html_resolve import (
    infer_template_id,
    looks_like_saas_dashboard,
    resolve_export_html_for_upload,
)


def _gen(*, code: str = "", files: list[GeneratedFile] | None = None) -> CodeGenerateResult:
    return CodeGenerateResult(
        summary="test",
        code=code,
        files=files or [],
        stack=["html"],
        model="test",
        provider="cyberforge",
    )


def _long_html(inner: str) -> str:
    pad = "x" * 400
    return f"<!DOCTYPE html><html><head><title>t</title></head><body>{inner}{pad}</body></html>"


def test_priority_assembled_over_preview_and_generation():
    ecommerce = _long_html('<button class="cart-btn">Panier</button>')
    dashboard = _long_html('<div class="saas-shell"><aside class="cf-sidebar"></aside></div>')
    gen = _gen(code=dashboard, files=[GeneratedFile(path="index.html", content=dashboard)])
    html, source, tid = resolve_export_html_for_upload(
        assembled_html=ecommerce,
        preview_html=dashboard,
        generation=gen,
        template_id="ecommerce_alimentaire",
    )
    assert source == "assembled_html"
    assert "cart-btn" in html
    assert tid == "ecommerce_alimentaire"


def test_preview_before_generation_code():
    preview = _long_html('<main id="app">Preview</main>')
    gen = _gen(code=_long_html("Old dashboard saas-shell"))
    html, source, _ = resolve_export_html_for_upload(
        preview_html=preview,
        generation=gen,
    )
    assert source == "preview_html"
    assert "Preview" in html


def test_generation_code_when_no_pipeline_html():
    code = _long_html("<h1>Fallback</h1>")
    html, source, _ = resolve_export_html_for_upload(generation=_gen(code=code))
    assert source == "generation.code"
    assert "Fallback" in html


def test_infer_template_id_from_sector_template():
    tid = infer_template_id(
        sector_template={"template_id": "ecommerce_alimentaire"},
    )
    assert tid == "ecommerce_alimentaire"


def test_looks_like_saas_dashboard():
    assert looks_like_saas_dashboard('<div class="saas-shell"></div>')
