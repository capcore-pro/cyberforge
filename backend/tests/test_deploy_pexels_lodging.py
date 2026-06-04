"""Requêtes Pexels hébergements camping — DeployAI."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "deploy_ai_test",
    Path(__file__).resolve().parents[1] / "agents" / "deploy_ai.py",
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_pexels_query_for_alt = _mod._pexels_query_for_alt
_detect_pexels_image_role = _mod._detect_pexels_image_role

_spec_tb = importlib.util.spec_from_file_location(
    "toolbox_media_test",
    Path(__file__).resolve().parents[1] / "tools" / "toolbox_media.py",
)
assert _spec_tb and _spec_tb.loader
_tb = importlib.util.module_from_spec(_spec_tb)
_spec_tb.loader.exec_module(_tb)
_pexels_pick_src_url = _tb.pexels_pick_src_url


def test_mobil_home_confort_query() -> None:
    q = _pexels_query_for_alt(
        "Mobil-home Confort",
        sector="camping / plein air",
        project_type="site_reservation",
    )
    assert q == "mobile home camping exterior"


def test_chalet_query() -> None:
    q = _pexels_query_for_alt(
        "Chalet premium",
        sector="camping",
        project_type="site_reservation",
    )
    assert q == "wooden chalet forest"


def test_pexels_pick_src_url_sizes() -> None:
    src = {
        "original": "https://pexels.com/original.jpg",
        "large2x": "https://pexels.com/large2x.jpg",
        "large": "https://pexels.com/large.jpg",
        "medium": "https://pexels.com/medium.jpg",
        "small": "https://pexels.com/small.jpg",
    }
    assert _pexels_pick_src_url(src, role="hero") == "https://pexels.com/large2x.jpg"
    assert _pexels_pick_src_url(src, role="card") == "https://pexels.com/large.jpg"
    assert _pexels_pick_src_url(src, role="default") == "https://pexels.com/large2x.jpg"


def test_detect_hero_role() -> None:
    html = '<section class="hero-slider"><div class="hero-slide"><img class="pexels-inject" alt="x">'
    pos = html.index("<img")
    assert _detect_pexels_image_role('class="pexels-inject"', html, pos) == "hero"


def test_generic_vitrine_uses_alt() -> None:
    q = _pexels_query_for_alt(
        "Boulangerie artisanale",
        sector="commerce",
        project_type="vitrine_next",
    )
    assert q == "Boulangerie artisanale"
