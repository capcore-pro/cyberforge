"""Slots desktop — libellés modules avec esperluette non échappée."""

from __future__ import annotations

from agents.content_slots import build_desktop_slots


def test_desktop_module_labels_keep_ampersand() -> None:
    slots = build_desktop_slots("desktop_artisan", "Dupont & Fils", {"PRIMARY_COLOR": "#0078D4"})
    assert slots["MODULE_1"] == "Devis & chantiers"
    assert "&amp;" not in slots["MODULE_1"]
    assert slots["CLIENT_NAME"] == "Dupont &amp; Fils"
