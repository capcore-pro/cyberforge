"""
Password protection for managed vitrines.

We intentionally store a reversible encrypted password so CyberForge can display
the current password to the operator (as requested), while still keeping it
encrypted at rest in Supabase.
"""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

from config import plain_secret_str
from db.managed_projects_store import ManagedProjectAuthRow, ManagedProjectsStore
from tools.demo_password_vault import decrypt_demo_password, encrypt_demo_password


class VitrineAuthError(Exception):
    pass


def generate_vitrine_password(length: int = 14) -> str:
    # Avoid ambiguous characters; keep it copy/paste friendly.
    alphabet = string.ascii_letters + string.digits
    # Ensure at least some complexity
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(max(10, length)))
        if any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd):
            return pwd


def decrypt_password(auth: ManagedProjectAuthRow | None) -> str | None:
    return decrypt_demo_password(auth.password_encrypted if auth else None)


async def ensure_auth_row(store: ManagedProjectsStore, project_id: str) -> ManagedProjectAuthRow:
    existing = await store.get_project_auth(project_id)
    if existing:
        return existing
    return await store.upsert_project_auth(project_id, enabled=False, client_email=None)


async def set_password(
    *,
    store: ManagedProjectsStore,
    project_id: str,
    password: str,
) -> ManagedProjectAuthRow:
    plain = (password or "").strip()
    if len(plain) < 8:
        raise VitrineAuthError("Mot de passe trop court (min 8).")
    encrypted = encrypt_demo_password(plain)
    now = datetime.now(tz=UTC).isoformat()
    return await store.upsert_project_auth(
        project_id,
        password_encrypted=encrypted,
        password_updated_at=now,
    )


async def set_auth_settings(
    *,
    store: ManagedProjectsStore,
    project_id: str,
    enabled: bool | None,
    client_email: str | None,
) -> ManagedProjectAuthRow:
    email = (client_email or "").strip() or None
    return await store.upsert_project_auth(project_id, enabled=enabled, client_email=email)


def email_matches(auth: ManagedProjectAuthRow | None, email: str) -> bool:
    wanted = (email or "").strip().lower()
    stored = (auth.client_email or "").strip().lower() if auth else ""
    return bool(wanted and stored and wanted == stored)

