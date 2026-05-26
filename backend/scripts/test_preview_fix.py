"""Script manuel — vérifie la reconstruction HTML depuis JSON enveloppé."""

from __future__ import annotations

import json

from tools.demo_preview_html import build_demo_preview_html
from tools.generation_sources import is_usable_preview_html, normalize_generation_sources

SAMPLE_TSX = """import React from 'react';

export default function App() {
  return (
    <main className="min-h-screen bg-amber-50 text-amber-900">
      <h1>Café du Centre</h1>
      <p>Menu et réservations.</p>
    </main>
  );
}
"""

blob = json.dumps(
    {"summary": "x", "code": SAMPLE_TSX, "files": [{"path": "src/App.tsx", "content": SAMPLE_TSX}]},
    ensure_ascii=False,
)
files = [{"path": "src/App.tsx", "content": blob}]
norm_files, code = normalize_generation_sources(files, None)
html = build_demo_preview_html(norm_files, title="Café test", code=code)
print("wrapped usable:", is_usable_preview_html(html))
print("wrapped has_title:", "Café du Centre" in html)
print("wrapped length:", len(html))

# HTML de test minimal (étape 4 — iframe srcdoc)
test_html = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8" />
<title>Test iframe CyberForge</title>
<style>body{font-family:system-ui;background:#0a0a0f;color:#e2e8f0;padding:2rem}
h1{color:#22d3ee}</style></head>
<body><h1>HTML de test valide</h1><p>Si vous voyez ceci, l'iframe srcDoc fonctionne.</p></body></html>"""
out = __file__.replace("test_preview_fix.py", "test_iframe_preview.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(test_html)
print("test_html_file:", out)
print("test_html usable:", is_usable_preview_html(test_html))
