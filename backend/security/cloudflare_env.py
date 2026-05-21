"""
Credentials Cloudflare Pages — uniquement via backend/.env (pas le coffre).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

_credentials: "CloudflareCredentials | None" = None


@dataclass(frozen=True)
class CloudflareCredentials:
    account_id: str
    api_token: str


def load_cloudflare_from_env(settings: Settings | None = None) -> CloudflareCredentials | None:
    """Charge CLOUDFLARE_* depuis l'environnement (appelé au démarrage)."""
    global _credentials
    cfg = settings or get_settings()
    account_id = plain_secret_str(cfg.cloudflare_account_id)
    api_token = plain_secret_str(cfg.cloudflare_api_token)
    if account_id and api_token:
        _credentials = CloudflareCredentials(
            account_id=account_id,
            api_token=api_token,
        )
        logger.info("Cloudflare Pages : credentials chargés depuis backend/.env")
    else:
        _credentials = None
        logger.info(
            "Cloudflare Pages : non configuré (CLOUDFLARE_ACCOUNT_ID / "
            "CLOUDFLARE_API_TOKEN dans backend/.env)"
        )
    return _credentials


def get_cloudflare_credentials() -> CloudflareCredentials | None:
    return _credentials


def cloudflare_configured() -> bool:
    return _credentials is not None
