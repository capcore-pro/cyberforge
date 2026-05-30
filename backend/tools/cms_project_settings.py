"""Paramètres CMS par projet managé."""

from __future__ import annotations

from urllib.parse import urlencode, urlparse, urlunparse


def build_cms_login_url(site_url: str | None) -> str | None:
    """URL d'accès client au panneau CMS (?cms=1)."""
    raw = (site_url or "").strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw.lstrip('/')}"
    parsed = urlparse(raw)
    query = urlencode({"cms": "1"})
    if parsed.query:
        if "cms=1" in parsed.query:
            return raw
        new_query = f"{parsed.query}&{query}"
    else:
        new_query = query
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )
