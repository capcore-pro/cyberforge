"""
Rendu local VisionUI — fallback lorsque Replicate est indisponible.
Expose l'HTML généré pour aperçu iframe côté Générateur (pas de capture distante).
"""

from __future__ import annotations

import base64
from html import escape

from pydantic import BaseModel, Field


class VisionPreviewResult(BaseModel):
    """Résultat d'aperçu VisionUI."""

    source: str = Field(description="replicate | local")
    screenshot_url: str | None = None
    local_html: str | None = None
    message: str = ""


def local_html_preview(html: str, *, title: str = "Aperçu") -> VisionPreviewResult:
    """Fallback : le Générateur affiche l'HTML en iframe (rendu local)."""
    cleaned = html.strip()
    if not cleaned:
        return VisionPreviewResult(
            source="local",
            message="HTML vide — aperçu local indisponible.",
        )
    return VisionPreviewResult(
        source="local",
        local_html=cleaned,
        message=f"Rendu HTML local ({len(cleaned.encode('utf-8'))} octets).",
    )


def local_placeholder_screenshot(title: str) -> str:
    """
    Miniature SVG (data URL) affichée si Replicate échoue mais qu'on veut une image.
    L'aperçu principal reste l'iframe HTML.
    """
    safe = escape(title[:80] or "CyberForge")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f0a1a"/>
      <stop offset="100%" stop-color="#1a1030"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#g)"/>
  <text x="640" y="340" fill="#00ffc8" font-family="monospace" font-size="28" text-anchor="middle">VisionUI</text>
  <text x="640" y="390" fill="#a78bfa" font-family="sans-serif" font-size="18" text-anchor="middle">{safe}</text>
  <text x="640" y="430" fill="#6b7280" font-family="sans-serif" font-size="14" text-anchor="middle">Aperçu HTML local</text>
</svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
