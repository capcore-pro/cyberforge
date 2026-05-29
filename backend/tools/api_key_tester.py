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
        if key in ("anthropic", "deepseek", "replicate", "tavily"):
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


def _test_v0(token: str) -> tuple[bool, str]:
    headers = {"Authorization": f"Bearer {secret_for_http_header(token)}"}
    return _http_ok("GET", "https://api.v0.dev/v1/me", headers=headers)


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
