"""Tests normalisation sources génération / preview HTML."""

import json

from tools.demo_preview_html import build_demo_preview_html
from tools.generation_sources import (
    is_usable_preview_html,
    normalize_generation_sources,
)

SAMPLE_TSX = """import React from 'react';

export default function App() {
  return (
    <main className="min-h-screen bg-amber-50 text-amber-900">
      <h1>Café du Centre</h1>
      <p>Menu et réservations.</p>
      <button>Réserver</button>
    </main>
  );
}
"""

JSON_WRAPPED = json.dumps(
    {
        "summary": "Landing café",
        "code": SAMPLE_TSX,
        "files": [{"path": "src/App.tsx", "content": SAMPLE_TSX}],
    },
    ensure_ascii=False,
)


def test_normalize_json_wrapped_file_content() -> None:
    files = [{"path": "src/App.tsx", "content": JSON_WRAPPED}]
    norm_files, code = normalize_generation_sources(files, None)
    assert code and "Café du Centre" in code
    assert "import React" in norm_files[0]["content"]


def test_build_preview_from_json_wrapped() -> None:
    files = [{"path": "src/App.tsx", "content": JSON_WRAPPED}]
    html = build_demo_preview_html(files, title="Café test")
    assert is_usable_preview_html(html)
    assert "Café du Centre" in html
    assert "<!DOCTYPE html>" in html


def test_detect_broken_preview() -> None:
    broken = """<!DOCTYPE html><html><body><div id="cf-demo-root">\\n</div></body></html>"""
    assert not is_usable_preview_html(broken)
