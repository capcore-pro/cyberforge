"""Test E2E — génération vitrine + push GitHub (sans Vercel)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config  # noqa: F401

from config import get_settings, plain_secret_str
from tools.export_github import push_vitrine_site_to_github, vitrine_branch_name
from tools.vitrine.build import build_vitrine_site


PROMPT = (
    "Site vitrine pour Boulangerie Le Fournil, artisan boulanger à Nantes. "
    "Pain au levain, viennoiseries, commande en ligne. Ton chaleureux et local."
)


async def main() -> None:
    settings = get_settings()
    print("=== build_vitrine_site ===")
    result = await build_vitrine_site(
        PROMPT,
        project_type_label="Site vitrine",
        settings=settings,
    )
    print("business:", result.content.meta.businessName)
    print("dir:", result.output_dir)
    print("files:", result.file_count)
    print("images:", result.images_resolved)

    if not plain_secret_str(settings.github_token):
        print("GITHUB_TOKEN absent — skip push")
        return

    files: dict[str, str] = {}
    for rel in result.output_dir.rglob("*"):
        if not rel.is_file():
            continue
        rel_posix = rel.relative_to(result.output_dir).as_posix()
        if "node_modules" in rel_posix or ".next" in rel_posix:
            continue
        try:
            files[rel_posix] = rel.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

    slug = vitrine_branch_name(result.content.meta.businessName)
    print("=== push_vitrine_site_to_github ===")
    url = await push_vitrine_site_to_github(
        branch_slug=slug,
        files=files,
        settings=settings,
    )
    print("github:", url)
    print("branch:", slug)


if __name__ == "__main__":
    asyncio.run(main())
