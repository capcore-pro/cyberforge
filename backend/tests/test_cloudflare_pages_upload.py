"""Tests déploiement Cloudflare — cache-bust et marqueurs HTML."""

from tools.cloudflare_pages import (
    REDIRECTS_ASSET_PATH,
    REDIRECTS_MANIFEST_PATH,
    ROOT_STUB_MANIFEST_PATH,
    _file_digest,
    _validate_manifest_covers_uploads,
    apply_deploy_cache_bust,
    build_deploy_zip,
    build_pages_manifest,
    files_from_deploy_zip,
    pages_asset_path_for_token,
    pages_asset_path_legacy_for_token,
    public_demo_url_for_token,
    sanitize_manifest_entries,
    zip_contains_marker,
)
from tools.standalone_demo_html import build_task_manager_standalone_html, wrap_with_password_gate


def test_pages_asset_paths_flat_and_legacy() -> None:
    # pages_asset_path_for_token kept for backward compat (legacy u-prefix flat path)
    assert pages_asset_path_for_token("abc") == "uabc.html"
    # pages_asset_path_legacy_for_token is now the PRIMARY deploy path
    assert pages_asset_path_legacy_for_token("abc") == "d/abc/index.html"
    assert public_demo_url_for_token("abc") == (
        "https://cyberforge-demos.pages.dev/d/abc"
    )


def test_pages_slug_avoids_manifest_path_starting_with_dash() -> None:
    assert pages_asset_path_for_token("-aap88BoxGWL481C0VQfr8") == (
        "u-aap88BoxGWL481C0VQfr8.html"
    )
    assert pages_asset_path_legacy_for_token("-aap88BoxGWL481C0VQfr8") == (
        "d/-aap88BoxGWL481C0VQfr8/index.html"
    )


def test_deploy_demo_uses_directory_path() -> None:
    """Vérifie que le chemin primaire de déploiement est d/{slug}/index.html."""
    token = "abc123"
    primary = pages_asset_path_legacy_for_token(token)
    assert primary == "d/abc123/index.html"
    # Le chemin doit passer la validation du manifest
    from tools.cloudflare_pages import _VALID_MANIFEST_PATH
    assert _VALID_MANIFEST_PATH.match(primary)
    # L'URL publique pointe vers /d/{slug} sans slash final
    url = public_demo_url_for_token(token)
    assert url == "https://cyberforge-demos.pages.dev/d/abc123"


def test_build_pages_manifest_includes_redirects_no_stub_by_default() -> None:
    manifest = build_pages_manifest({"udemo.html": "deadbeef"})
    assert REDIRECTS_MANIFEST_PATH in manifest
    assert manifest["/udemo.html"] == "deadbeef"
    assert ROOT_STUB_MANIFEST_PATH not in manifest


def test_sanitize_manifest_entries_drops_obsolete_paths() -> None:
    entries = sanitize_manifest_entries(
        {
            "uabc.html": "aaa",
            "d/abc/index.html": "bbb",
            "index.html": "ccc",
            "d/nested/too/deep/index.html": "ddd",
        }
    )
    assert entries == {"uabc.html": "aaa", "d/abc/index.html": "bbb"}


def test_validate_manifest_covers_uploads() -> None:
    # Use the primary deploy path (d/{slug}/index.html)
    path = pages_asset_path_legacy_for_token("abc")
    body = b"<html></html>"
    digest = _file_digest(path, body)
    manifest = build_pages_manifest({path: digest})
    _validate_manifest_covers_uploads(manifest, {path: body})


def test_apply_deploy_cache_bust_changes_digest() -> None:
    # Use the primary deploy path (d/{slug}/index.html)
    path = pages_asset_path_legacy_for_token("abc")
    html = "<!DOCTYPE html><html><body>ok</body></html>"
    d1 = _file_digest(path, html.encode())
    d2 = _file_digest(path, apply_deploy_cache_bust(html).encode())
    assert d1 != d2
    assert "cf-deploy:" in apply_deploy_cache_bust(html)


def test_zip_contains_password_toggle_after_gate() -> None:
    inner = build_task_manager_standalone_html(title="Test", sources="")
    gated = wrap_with_password_gate(inner, "secret-demo", title="Test")
    # Primary deploy path is now d/{slug}/index.html
    path = pages_asset_path_legacy_for_token("tok1")
    zip_bytes = build_deploy_zip({path: gated.encode("utf-8"), REDIRECTS_ASSET_PATH: b"/d/:token /u:token.html 200\n"})
    assert zip_contains_marker(zip_bytes, "cf-password-toggle")


def test_build_deploy_zip_roundtrip() -> None:
    # Primary deploy path is now d/{slug}/index.html
    path = pages_asset_path_legacy_for_token("demo1")
    files = {path: b"<html>ok</html>", REDIRECTS_ASSET_PATH: b"/d/:token /u:token.html 200\n"}
    zip_bytes = build_deploy_zip(files)
    assert zip_bytes[:2] == b"PK"
    restored = files_from_deploy_zip(zip_bytes)
    assert restored == files


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
