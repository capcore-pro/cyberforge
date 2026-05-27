"""Crée le dépôt GitHub capcore-pro/vitrines s'il n'existe pas."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config  # noqa: F401

from config import get_settings, plain_secret_str
from tools.export_github import DEFAULT_VITRINES_REPO, ensure_github_repo


async def main() -> None:
    settings = get_settings()
    token = plain_secret_str(settings.github_token)
    if not token:
        raise SystemExit("GITHUB_TOKEN manquant dans backend/.env")

    repo = (settings.vitrines_github_repo or DEFAULT_VITRINES_REPO).strip()
    created = await ensure_github_repo(repo, token)
    if created:
        print(f"CREATED https://github.com/{repo}")
    else:
        print(f"EXISTS https://github.com/{repo}")


if __name__ == "__main__":
    asyncio.run(main())
