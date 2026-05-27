"""Tests export GitHub vitrines — branche dédiée par site."""

import asyncio

import pytest

from tools.export_github import vitrine_branch_name


def test_vitrine_branch_name_sanitizes() -> None:
    assert vitrine_branch_name("Plomberie Dubois!") == "plomberie-dubois"
    assert vitrine_branch_name("  Site   vitrine  ") == "site-vitrine"


def test_push_vitrine_site_to_github_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import export_github as mod

    calls: list[str] = []

    async def fake_ensure(repo: str, token: str, **kwargs) -> bool:
        calls.append(f"ensure:{repo}")
        return False

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url: str, **kwargs):
            calls.append(url)
            if "git/blobs" in url:
                return _Resp(201, {"sha": f"blob-{len(calls)}"})
            if "git/trees" in url:
                return _Resp(201, {"sha": "tree-sha"})
            if "git/commits" in url:
                return _Resp(201, {"sha": "commit-sha"})
            if "git/refs" in url and url.endswith("/git/refs"):
                return _Resp(201, {})
            return _Resp(404, {})

        async def get(self, url: str, **kwargs):
            if "git/ref/heads/" in url:
                return _Resp(404, {})
            return _Resp(404, {})

        async def patch(self, url: str, **kwargs):
            return _Resp(200, {})

    class _Resp:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    monkeypatch.setattr(mod, "ensure_github_repo", fake_ensure)
    monkeypatch.setattr(mod.httpx, "AsyncClient", FakeClient)

    from config import Settings

    url = asyncio.run(
        mod.push_vitrine_site_to_github(
            branch_slug="plomberie-dubois",
            files={"package.json": "{}", "content/site.json": "{}"},
            settings=Settings(github_token="gh_test"),
            repo="mathiasgibiard-dotcom/vitrines",
        )
    )

    assert url == "https://github.com/mathiasgibiard-dotcom/vitrines/tree/plomberie-dubois"
    assert any("ensure:mathiasgibiard-dotcom/vitrines" in c for c in calls)
