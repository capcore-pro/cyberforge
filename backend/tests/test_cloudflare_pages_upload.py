"""Tests déploiement Cloudflare — cache-bust et marqueurs HTML."""

from tools.cloudflare_pages import (
    REDIRECTS_MANIFEST_PATH,
    _file_digest,
    _validate_manifest_covers_uploads,
    apply_deploy_cache_bust,
    build_pages_manifest,
    pages_asset_path_for_token,
    pages_asset_path_legacy_for_token,
    public_demo_url_for_token,
)


def test_pages_asset_paths_flat_and_legacy() -> None:
    assert pages_asset_path_for_token("abc") == "uabc.html"
    assert pages_asset_path_legacy_for_token("abc") == "d/uabc/index.html"
    assert public_demo_url_for_token("abc").endswith("/uabc.html")


def test_pages_slug_avoids_manifest_path_starting_with_dash() -> None:
    assert pages_asset_path_for_token("-aap88BoxGWL481C0VQfr8") == (
        "u-aap88BoxGWL481C0VQfr8.html"
    )


def test_build_pages_manifest_includes_redirects() -> None:
    manifest = build_pages_manifest({"udemo.html": "deadbeef"})
    assert REDIRECTS_MANIFEST_PATH in manifest
    assert manifest["/udemo.html"] == "deadbeef"


def test_validate_manifest_covers_uploads() -> None:
    path = pages_asset_path_for_token("abc")
    body = b"<html></html>"
    digest = _file_digest(path, body)
    manifest = build_pages_manifest({path: digest})
    _validate_manifest_covers_uploads(manifest, {path: body})


def test_apply_deploy_cache_bust_changes_digest() -> None:
    path = pages_asset_path_for_token("abc")
    html = "<!DOCTYPE html><html><body>ok</body></html>"
    d1 = _file_digest(path, html.encode())
    d2 = _file_digest(path, apply_deploy_cache_bust(html).encode())
    assert d1 != d2
    assert "cf-deploy:" in apply_deploy_cache_bust(html)


def test_gate_markers_in_busted_html() -> None:
    from tools.standalone_demo_html import build_standalone_demo_html

    raw = build_standalone_demo_html(
        'export default function App(){ const [tasks,setTasks]=useState([]); const addTask=()=>{}; return null;}',
        title="Test",
        password="secret",
    )
    busted = apply_deploy_cache_bust(raw)
    assert "cf-password-toggle" in busted
    assert "cf-lock-btn" in busted
