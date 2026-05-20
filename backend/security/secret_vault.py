"""
Coffre local chiffré pour stocker les clés API (LLM, etc.).

- Chiffrement: Fernet (AES128-CBC + HMAC) via `cryptography`.
- Clé dérivée d'un mot de passe utilisateur (PBKDF2-HMAC-SHA256).
- Stockage local: fichier JSON dans AppData/Local (Windows).
"""

from __future__ import annotations

import base64
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class VaultLockedError(Exception):
    pass


class VaultInvalidPasswordError(Exception):
    pass


@dataclass(frozen=True)
class VaultStatus:
    has_vault: bool
    locked: bool
    configured: dict[str, bool]


def _default_vault_path() -> Path:
    # Windows-first (projet actuel). Fallback sur ~/.cyberforge
    base = (
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("APPDATA")
        or str(Path.home())
    )
    root = Path(base) / "CyberForge"
    root.mkdir(parents=True, exist_ok=True)
    return root / "secrets.v1.json"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode("ascii"))


def _derive_fernet_key(password: str, *, salt: bytes, iterations: int) -> bytes:
    if not password:
        raise VaultInvalidPasswordError("Mot de passe requis.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)  # Fernet expects urlsafe base64


class SecretVault:
    """
    Coffre chiffré, chargé/déverrouillé explicitement.
    Les secrets déchiffrés ne sont conservés qu'en mémoire.
    """

    _ITERATIONS = 390_000

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_vault_path()
        self._lock = threading.RLock()
        self._secrets: dict[str, str] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def has_vault(self) -> bool:
        return self._path.exists()

    def is_locked(self) -> bool:
        with self._lock:
            return self._secrets is None

    def status(self) -> VaultStatus:
        with self._lock:
            configured = {
                "openai": bool(self._secrets and self._secrets.get("OPENAI_API_KEY")),
                "anthropic": bool(
                    self._secrets and self._secrets.get("ANTHROPIC_API_KEY")
                ),
                "deepseek": bool(
                    self._secrets and self._secrets.get("DEEPSEEK_API_KEY")
                ),
                "gemini": bool(
                    self._secrets and self._secrets.get("GOOGLE_GENERATIVE_AI_API_KEY")
                ),
            }
            return VaultStatus(
                has_vault=self.has_vault(),
                locked=self._secrets is None,
                configured=configured,
            )

    def lock(self) -> None:
        with self._lock:
            self._secrets = None

    def peek(self, key: str) -> str | None:
        """Lit une clé si le coffre est déverrouillé ; None si verrouillé ou absent."""
        with self._lock:
            if self._secrets is None:
                return None
            value = self._secrets.get(key)
            return value if value else None

    def get(self, key: str) -> str | None:
        with self._lock:
            if self._secrets is None:
                raise VaultLockedError("Coffre verrouillé.")
            value = self._secrets.get(key)
            return value if value else None

    def unlock(self, password: str) -> None:
        with self._lock:
            if not self._path.exists():
                # Pas de coffre => reste verrouillé
                self._secrets = {}
                return

            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload.get("version") != 1:
                raise ValueError("Version de coffre non supportée.")

            kdf_info = payload.get("kdf") or {}
            salt = _b64d(str(kdf_info.get("salt", "")))
            iterations = int(kdf_info.get("iterations") or self._ITERATIONS)
            ciphertext = str(payload.get("ciphertext") or "")

            fernet_key = _derive_fernet_key(password, salt=salt, iterations=iterations)
            f = Fernet(fernet_key)
            try:
                clear = f.decrypt(ciphertext.encode("ascii"))
            except InvalidToken as exc:
                raise VaultInvalidPasswordError("Mot de passe invalide.") from exc

            secrets = json.loads(clear.decode("utf-8"))
            if not isinstance(secrets, dict):
                raise ValueError("Coffre corrompu (format).")
            self._secrets = {
                str(k): str(v) for k, v in secrets.items() if isinstance(v, str)
            }

    def _decrypt_payload(self, password: str, payload: dict[str, Any]) -> dict[str, str]:
        kdf_info = payload.get("kdf") or {}
        salt = _b64d(str(kdf_info.get("salt", "")))
        iterations = int(kdf_info.get("iterations") or self._ITERATIONS)
        ciphertext = str(payload.get("ciphertext") or "")
        fernet_key = _derive_fernet_key(password, salt=salt, iterations=iterations)
        f = Fernet(fernet_key)
        try:
            clear = f.decrypt(ciphertext.encode("ascii"))
        except InvalidToken as exc:
            raise VaultInvalidPasswordError("Mot de passe invalide.") from exc
        secrets = json.loads(clear.decode("utf-8"))
        if not isinstance(secrets, dict):
            raise ValueError("Coffre corrompu (format).")
        return {str(k): str(v) for k, v in secrets.items() if isinstance(v, str)}

    def save(self, password: str, *, secrets: dict[str, str | None]) -> None:
        """
        Ecrit le coffre chiffré sur disque, puis charge les secrets en mémoire.
        Fusionne avec le coffre existant ; seules les clés fournies sont mises à jour.
        """
        with self._lock:
            merged: dict[str, str] = {}
            if self._secrets is not None:
                merged = dict(self._secrets)
            elif self._path.exists():
                payload = json.loads(self._path.read_text(encoding="utf-8"))
                if payload.get("version") == 1:
                    merged = self._decrypt_payload(password, payload)

            for k, v in secrets.items():
                name = str(k)
                if not v:
                    continue
                merged[name] = str(v).strip()

            self._write_encrypted(password, merged)

    def _write_encrypted(self, password: str, secrets: dict[str, str]) -> None:
        salt = os.urandom(16)
        iterations = self._ITERATIONS
        fernet_key = _derive_fernet_key(password, salt=salt, iterations=iterations)
        f = Fernet(fernet_key)
        clear = json.dumps(secrets, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        ciphertext = f.encrypt(clear).decode("ascii")
        payload: dict[str, Any] = {
            "version": 1,
            "kdf": {
                "name": "pbkdf2_sha256",
                "salt": _b64e(salt),
                "iterations": iterations,
            },
            "ciphertext": ciphertext,
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._secrets = dict(secrets)

    def change_master_password(self, old_password: str, new_password: str) -> None:
        """Déchiffre avec l'ancien mot de passe et rechiffre avec le nouveau."""
        with self._lock:
            if not self._path.exists():
                raise ValueError("Aucun coffre existant. Enregistrez d'abord vos clés.")
            if not new_password.strip():
                raise VaultInvalidPasswordError("Nouveau mot de passe requis.")
            if old_password == new_password:
                raise ValueError(
                    "Le nouveau mot de passe doit être différent de l'ancien."
                )

            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload.get("version") != 1:
                raise ValueError("Version de coffre non supportée.")

            secrets = self._decrypt_payload(old_password, payload)
            self._write_encrypted(new_password, secrets)


_vault: SecretVault | None = None


def get_secret_vault() -> SecretVault:
    global _vault
    if _vault is None:
        _vault = SecretVault()
    return _vault

