"""Config runtime injectée dans les démos Cloudflare (token, API, URL publique)."""

from __future__ import annotations

import json


def inject_demo_runtime_config(
    html: str,
    *,
    token: str,
    project_title: str,
    demo_url: str,
    api_base_url: str,
) -> str:
    """
    Insère un bloc JSON lisible par premium_interaction_scripts (formulaire CapCore).
    """
    payload = {
        "token": token.strip(),
        "projectTitle": (project_title or "Démo").strip() or "Démo",
        "demoUrl": demo_url.strip().rstrip("/"),
        "apiBase": api_base_url.strip().rstrip("/"),
    }
    blob = json.dumps(payload, ensure_ascii=False)
    blob = blob.replace("</", "<\\/")
    script = f'<script id="cf-demo-runtime" type="application/json">{blob}</script>'
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx >= 0:
        return html[:idx] + script + "\n" + html[idx:]
    return html + script
