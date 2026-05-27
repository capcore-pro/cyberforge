"""Tests ScaffoldRenderer — copie template + site.json."""

import json
import shutil
from pathlib import Path

import pytest

from tools.vitrine.content_schema import VitrineSiteContent
from tools.vitrine.scaffold_renderer import (
    load_example_content,
    render_vitrine_scaffold,
    vitrine_template_dir,
)


def test_vitrine_template_exists() -> None:
    assert vitrine_template_dir().is_dir()
    assert (vitrine_template_dir() / "package.json").is_file()


def test_render_vitrine_scaffold_writes_site_json(tmp_path: Path) -> None:
    content = load_example_content()
    result = render_vitrine_scaffold(content, output_dir=tmp_path / "out")

    assert result.output_dir == (tmp_path / "out").resolve()
    assert result.site_json_path.is_file()
    assert (result.output_dir / "app" / "page.tsx").is_file()
    assert "node_modules" not in result.files

    raw = json.loads(result.site_json_path.read_text(encoding="utf-8"))
    parsed = VitrineSiteContent.model_validate(raw)
    assert parsed.meta.businessName == content.meta.businessName


def test_load_example_content_matches_template() -> None:
    example = load_example_content()
    assert example.navigation[0].href == "/"
    assert len(example.home.servicesPreview) >= 1


@pytest.fixture
def vitrine_build_dir(tmp_path: Path):
    out = tmp_path / "plombier-test"
    yield out
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
