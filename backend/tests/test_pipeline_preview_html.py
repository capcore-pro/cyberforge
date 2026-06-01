"""Persistance preview_html — assembled_html prioritaire."""

from __future__ import annotations

from tools.export_html_resolve import (
    force_finalize_preview_from_assembled,
    resolve_pipeline_preview_html,
)


def test_resolve_pipeline_preview_prefers_assembled() -> None:
    html = (
        "<!DOCTYPE html><html><head><title>Garage</title></head>"
        "<body><main>" + ("x" * 500) + "</main></body></html>"
    )
    preview, assembled = resolve_pipeline_preview_html(
        assembled_html=html,
        preview_html=None,
        sector_template_html=None,
    )
    assert preview
    assert assembled == preview
    assert "Garage" in preview


def test_force_finalize_prefers_state_assembled() -> None:
    html = (
        "<!DOCTYPE html><html><head><title>Garage</title></head>"
        "<body><main>" + ("z" * 500) + "</main></body></html>"
    )
    preview, assembled = force_finalize_preview_from_assembled(
        state_assembled_html=html,
        preview_html=None,
        assembled_html=None,
        sector_template_html=None,
        generation=None,
    )
    assert preview == assembled
    assert "Garage" in (preview or "")


def test_resolve_pipeline_preview_uses_sector_template_when_no_state() -> None:
    html = (
        "<!DOCTYPE html><html><head><title>App</title></head>"
        "<body><div id=\"dataTable\">" + ("y" * 500) + "</div></body></html>"
    )
    preview, assembled = resolve_pipeline_preview_html(
        assembled_html=None,
        preview_html=None,
        sector_template_html=html,
    )
    assert preview
    assert assembled == preview
