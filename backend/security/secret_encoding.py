"""
Normalisation UTF-8 des secrets (coffre, .env, variables d'environnement).

Évite les erreurs « ascii codec can't encode character » lors des appels HTTP
(Authorization) quand une clé a été lue avec un mauvais encodage Windows (cp1252).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SECRET_ENV_NAMES = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
        "V0_API_KEY",
        "REPLICATE_API_KEY",
        "RAILWAY_API_KEY",
        "GITHUB_TOKEN",
        "VERCEL_TOKEN",
        "BREVO_API_KEY",
        "TAVILY_API_KEY",
        "UNSPLASH_ACCESS_KEY",
        "PEXELS_API_KEY",
        "FIRECRAWL_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_R2_ACCOUNT_ID",
        "STRIPE_SECRET_KEY",
        "STRIPE_ECOMMERCE_WEBHOOK_SECRET",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SERVICE_KEY",
    }
)


def _decode_bytes_as_utf8(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _repair_misdecoded_utf8(text: str) -> str:
    """
    Tente de réparer une chaîne UTF-8 lue à tort en latin-1/cp1252 (octets → caractères).
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def normalize_secret_text(value: Any) -> str:
    """
    Force une représentation str cohérente en UTF-8 (strip, BOM, round-trip).
    Retourne une chaîne vide si la valeur est absente.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = _decode_bytes_as_utf8(value)
    else:
        text = str(value)

    text = text.strip().strip("\ufeff")
    if not text:
        return ""

    # Round-trip UTF-8 (rejette les surrogates invalides)
    text = text.encode("utf-8", errors="surrogatepass").decode(
        "utf-8", errors="replace"
    )
    return text


def secret_for_http_header(value: Any) -> str:
    """
    Valeur utilisable dans un en-tête HTTP (ASCII).
    Les clés API réelles sont ASCII ; on répare d'abord un mauvais encodage.
    """
    text = normalize_secret_text(value)
    if not text:
        return ""
    try:
        text.encode("ascii")
        return text
    except UnicodeEncodeError:
        repaired = _repair_misdecoded_utf8(text)
        try:
            repaired.encode("ascii")
            if repaired != text:
                logger.warning(
                    "Clé API réparée (encodage latin-1 → UTF-8) avant envoi HTTP."
                )
            return repaired
        except UnicodeEncodeError:
            ascii_only = repaired.encode("ascii", errors="ignore").decode("ascii")
            if ascii_only != repaired:
                logger.warning(
                    "Caractères non-ASCII retirés d'une clé API avant envoi HTTP."
                )
            return ascii_only


def read_env_secret(name: str) -> str:
    """Lit une variable d'environnement en forçant l'interprétation UTF-8."""
    raw = os.environ.get(name)
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return normalize_secret_text(raw)
    return normalize_secret_text(raw)


def normalize_secret_map(secrets: dict[str, Any]) -> dict[str, str]:
    """Normalise toutes les entrées d'un coffre déchiffré."""
    out: dict[str, str] = {}
    for key, value in secrets.items():
        if not isinstance(value, str):
            continue
        normalized = normalize_secret_text(value)
        if normalized:
            out[str(key)] = normalized
    return out


def is_known_secret_env(name: str) -> bool:
    return name in _SECRET_ENV_NAMES or name.endswith("_API_KEY") or name.endswith(
        "_TOKEN"
    )
