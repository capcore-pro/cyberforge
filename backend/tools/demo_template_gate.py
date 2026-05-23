"""Gate mot de passe partagé par tous les templates premium."""

from __future__ import annotations

from collections.abc import Callable

from tools.standalone_demo_html import wrap_with_password_gate


def build_gated_html(
    build_plain: Callable[..., str],
    password: str,
    *,
    title: str = "Démo CyberForge",
    **kwargs: object,
) -> str:
    """Enveloppe le HTML template avec wrap_with_password_gate."""
    plain = build_plain(**kwargs)
    gated = wrap_with_password_gate(plain, password.strip(), title=title)
    if "cf-password-toggle" not in gated:
        raise ValueError("Gate mot de passe invalide (cf-password-toggle manquant).")
    return gated
