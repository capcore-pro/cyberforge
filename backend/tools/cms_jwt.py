"""JWT minimal HS256 pour sessions CMS client (cookie httpOnly)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class CmsJwtError(Exception):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_cms_token(
    *,
    project_id: str,
    email: str,
    secret: str,
    ttl_seconds: int = 7 * 24 * 3600,
) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_obj = {
        "sub": project_id,
        "email": email.strip().lower(),
        "exp": int(time.time()) + ttl_seconds,
    }
    payload = _b64url_encode(json.dumps(payload_obj, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url_encode(signature)}"


def decode_cms_token(token: str, secret: str) -> dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise CmsJwtError("Token invalide.")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        provided = _b64url_decode(sig_b64)
    except Exception as exc:
        raise CmsJwtError("Signature invalide.") from exc
    if not hmac.compare_digest(expected, provided):
        raise CmsJwtError("Signature invalide.")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except json.JSONDecodeError as exc:
        raise CmsJwtError("Payload invalide.") from exc
    if not isinstance(payload, dict):
        raise CmsJwtError("Payload invalide.")
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or int(exp) < int(time.time()):
        raise CmsJwtError("Session expirée.")
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise CmsJwtError("Projet manquant dans le token.")
    return payload
