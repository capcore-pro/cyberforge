"""Tests déploiement Cloudflare Pages dédié."""

from tools.cloudflare_pages import (
    build_manifest_for_files,
    public_pages_url_for_project,
)


def test_public_pages_url_for_project() -> None:
    assert public_pages_url_for_project("capcore-pro-site") == (
        "https://capcore-pro-site.pages.dev"
    )


def test_build_manifest_for_files() -> None:
    body = b"<!DOCTYPE html><html></html>"
    manifest = build_manifest_for_files({"index.html": body})
    assert "/index.html" in manifest
    assert len(manifest["/index.html"]) == 32
