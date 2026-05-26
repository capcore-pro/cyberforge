"""Chiffrement réversible du mot de passe démo (notifications équipe uniquement)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings, plain_secret_str


def _fernet() -> Fernet:
    secret = plain_secret_str(get_settings().secret_key) or "change-me-in-production"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_demo_password(password: str) -> str:
    plain = (password or "").strip()
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_demo_password(encrypted: str | None) -> str | None:
    token = (encrypted or "").strip()
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
