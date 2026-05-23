"""URLs publiques des démos client."""

from config import get_settings


def unlock_demo_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_public_url.rstrip("/")
    return f"{base}/demo/{token}"
