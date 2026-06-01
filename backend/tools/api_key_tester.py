"""
Tests de validité des clés API (ping léger, sans exposer les secrets).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cockpit_connectors import get_connector
from security.secret_encoding import secret_for_http_header

logger = logging.getLogger(__name__)


def test_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    key = (provider or "").strip().lower()
    token = (api_key or "").strip()
    if not token:
        return False, "Clé manquante"

    try:
        if key == "anthropic":
            return _test_anthropic(token)
        if key == "deepseek":
            return _test_deepseek(token)
        if key in ("replicate", "tavily"):
            connector = get_connector(key, token)
            if connector is None:
                return False, "Connecteur indisponible"
            ok = connector.ping()
            return (True, "Connexion réussie") if ok else (False, "Clé refusée par le service")

        if key == "v0":
            return _test_v0(token)
        if key == "railway":
            return _test_railway(token)
        if key == "vercel":
            return _test_vercel(token)
        if key == "github":
            return _test_github(token)
        if key == "brevo":
            return _test_brevo(token)
        if key == "stripe":
            return _test_stripe(token)
        if key == "brave_search":
            return _test_brave_search(token)
        if key == "exa":
            return _test_exa(token)
        if key == "stitch":
            return _test_stitch(token)

        return False, f"Fournisseur inconnu : {provider}"
    except Exception as exc:
        logger.debug("test_api_key(%s) — %s", key, exc)
        return False, str(exc) or "Échec du test"


def _http_ok(method: str, url: str, **kwargs: Any) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.request(method, url, **kwargs)
        if response.status_code in (200, 201, 204):
            return True, "Connexion réussie"
        if response.status_code == 401:
            return False, "Clé invalide (401)"
        return False, f"Réponse HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc) or "Erreur réseau"


def _anthropic_headers(token: str) -> dict[str, str]:
    return {
        "x-api-key": secret_for_http_header(token),
        "anthropic-version": "2023-06-01",
    }


def _bearer_headers(token: str) -> dict[str, str]:
    raw = secret_for_http_header(token)
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    return {"Authorization": f"Bearer {raw}"}


def _test_anthropic(token: str) -> tuple[bool, str]:
    return _http_ok(
        "GET",
        "https://api.anthropic.com/v1/models",
        headers=_anthropic_headers(token),
    )


def _test_deepseek(token: str) -> tuple[bool, str]:
    return _http_ok(
        "GET",
        "https://api.deepseek.com/models",
        headers=_bearer_headers(token),
    )


def _test_v0(token: str) -> tuple[bool, str]:
    """
    Tente GET /v1/projects (API Platform v0).
    Si l'endpoint n'est pas disponible publiquement, accepte la clé sans requête.
    """
    cleaned = token.strip()
    if not cleaned:
        return False, "Clé manquante"

    url = "https://api.v0.dev/v1/projects"
    headers = _bearer_headers(cleaned)
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return True, "Clé acceptée (test API v0 indisponible)"

    if response.status_code in (200, 201, 204):
        return True, "Connexion réussie"
    if response.status_code == 401:
        return False, "Clé invalide (401)"
    if response.status_code == 403:
        return True, "Clé reconnue (accès limité au plan)"
    if response.status_code in (404, 405, 501, 502, 503):
        return True, "Clé acceptée (pas de test API public)"
    return False, f"Réponse HTTP {response.status_code}"


def _test_railway(token: str) -> tuple[bool, str]:
    headers = {
        "Authorization": f"Bearer {secret_for_http_header(token)}",
        "Content-Type": "application/json",
    }
    payload = {"query": "{ me { id email } }"}
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                "https://backboard.railway.com/graphql/v2",
                headers=headers,
                json=payload,
            )
        if response.status_code == 401:
            return False, "Clé invalide (401)"
        if response.status_code != 200:
            return False, f"Réponse HTTP {response.status_code}"
        data = response.json()
        if data.get("errors"):
            return False, "Clé refusée par Railway"
        return True, "Connexion réussie"
    except httpx.HTTPError as exc:
        return False, str(exc) or "Erreur réseau"


def _test_vercel(token: str) -> tuple[bool, str]:
    headers = {"Authorization": f"Bearer {secret_for_http_header(token)}"}
    return _http_ok("GET", "https://api.vercel.com/v2/user", headers=headers)


def _test_github(token: str) -> tuple[bool, str]:
    headers = {
        "Authorization": f"Bearer {secret_for_http_header(token)}",
        "Accept": "application/vnd.github+json",
    }
    return _http_ok("GET", "https://api.github.com/user", headers=headers)


def _test_brevo(token: str) -> tuple[bool, str]:
    headers = {"api-key": secret_for_http_header(token)}
    return _http_ok("GET", "https://api.brevo.com/v3/account", headers=headers)


def _test_stripe(token: str) -> tuple[bool, str]:
    headers = {"Authorization": f"Bearer {secret_for_http_header(token)}"}
    return _http_ok("GET", "https://api.stripe.com/v1/balance", headers=headers)


def _test_brave_search(token: str) -> tuple[bool, str]:
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": secret_for_http_header(token),
    }
    return _http_ok(
        "GET",
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params={"q": "test", "count": 1},
    )


def _test_exa(token: str) -> tuple[bool, str]:
    headers = {
        "Authorization": f"Bearer {secret_for_http_header(token)}",
        "Content-Type": "application/json",
    }
    return _http_ok(
        "POST",
        "https://api.exa.ai/search",
        headers=headers,
        json={"query": "test", "numResults": 1, "type": "auto"},
    )


def _test_stitch(token: str) -> tuple[bool, str]:
    """Validation légère — la clé Stitch est vérifiée au runtime par stitch_runner.mjs."""
    cleaned = token.strip()
    if len(cleaned) < 8:
        return False, "Clé trop courte"
    return True, "Format accepté (test complet au pipeline StitchAI)"
