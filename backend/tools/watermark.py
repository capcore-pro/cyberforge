"""
Watermark CyberForge — injection sur démos non converties et suppression à la livraison.
"""

from __future__ import annotations

import re

_WATERMARK_ID = "cyberforge-watermark"
_EXPIRY_ID = "cyberforge-expiry"

WATERMARK_HTML = """
<div id="cyberforge-watermark" style="
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 99999;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(201,168,76,0.4);
  border-radius: 10px;
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: Inter, sans-serif;
  font-size: 12px;
  color: #f0f0f0;
  pointer-events: none;
  user-select: none;
">
  <span style="
    color: #c9a84c;
    font-weight: 600;
    letter-spacing: 0.05em;
  ">⚡ CyberForge</span>
  <span style="color: #888">
    Démo — Non commercialisable
  </span>
</div>
"""

EXPIRY_BANNER_HTML = """
<div id="cyberforge-expiry" style="
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 99999;
  background: rgba(201,168,76,0.95);
  padding: 10px 20px;
  text-align: center;
  font-family: Inter, sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #000;
">
  ⚡ Cette démo expire le {expiry_date}
  — Contactez CapCore pour finaliser
</div>
"""

_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)
_BODY_OPEN_RE = re.compile(r"(<body[^>]*>)", re.IGNORECASE)
_WATERMARK_RE = re.compile(
    rf'<div id="{_WATERMARK_ID}".*?</div>',
    re.DOTALL | re.IGNORECASE,
)
_EXPIRY_RE = re.compile(
    rf'<div id="{_EXPIRY_ID}".*?</div>',
    re.DOTALL | re.IGNORECASE,
)


def inject_watermark(html: str) -> str:
    """Injecte le watermark dans le HTML."""
    if not html:
        return WATERMARK_HTML.strip()
    if _BODY_CLOSE_RE.search(html):
        return _BODY_CLOSE_RE.sub(f"{WATERMARK_HTML}\n</body>", html, count=1)
    return html + WATERMARK_HTML


def inject_expiry_banner(html: str, expiry_date: str) -> str:
    """Injecte une bannière d'expiration."""
    banner = EXPIRY_BANNER_HTML.replace("{expiry_date}", expiry_date)
    if _BODY_OPEN_RE.search(html):
        return _BODY_OPEN_RE.sub(rf"\1{banner}", html, count=1)
    return banner + html


def remove_watermark(html: str) -> str:
    """Supprime le watermark et la bannière d'expiration (livraison finale)."""
    cleaned = _WATERMARK_RE.sub("", html)
    return _EXPIRY_RE.sub("", cleaned)


def has_watermark(html: str) -> bool:
    """Indique si le HTML contient le watermark CyberForge."""
    return _WATERMARK_ID in (html or "")
