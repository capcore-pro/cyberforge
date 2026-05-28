from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from config import Settings, get_settings, plain_secret_str


class TavilyError(RuntimeError):
    pass


@dataclass(frozen=True)
class TavilyExtractResult:
    url: str
    raw_content: str
    images: list[str]


async def tavily_extract_one(
    url: str,
    *,
    query: str = "",
    extract_depth: str = "basic",
    include_images: bool = True,
    settings: Settings | None = None,
) -> TavilyExtractResult:
    """
    Tavily Extract API (POST https://api.tavily.com/extract).
    Docs: https://docs.tavily.com/documentation/api-reference/endpoint/extract
    """
    resolved = settings or get_settings()
    key = plain_secret_str(resolved.tavily_api_key)
    if not key:
        raise TavilyError("TAVILY_API_KEY non configuré.")

    clean = (url or "").strip()
    if not (clean.startswith("http://") or clean.startswith("https://")):
        raise TavilyError("URL invalide (http/https requis).")

    payload: dict[str, object] = {
        "urls": [clean],
        "extract_depth": extract_depth,
        "format": "markdown",
        "include_images": include_images,
    }
    if query.strip():
        payload["query"] = query.strip()
        payload["chunks_per_source"] = 3

    timeout = float(resolved.tavily_http_timeout_seconds or 25.0)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(
                "https://api.tavily.com/extract",
                headers=headers,
                content=json.dumps(payload),
            )
        except httpx.HTTPError as exc:
            raise TavilyError(f"Tavily HTTP error: {exc}") from exc

    if r.status_code >= 400:
        raise TavilyError(f"Tavily error {r.status_code}: {r.text[:500]}")

    data = r.json()
    results = data.get("results") or []
    if not results:
        failed = data.get("failed_results") or []
        if failed:
            raise TavilyError(f"Tavily extract failed: {failed[0]}")
        raise TavilyError("Tavily extract: aucun résultat.")

    first = results[0] or {}
    raw = str(first.get("raw_content") or "").strip()
    imgs = first.get("images") or []
    images: list[str] = [str(x) for x in imgs if isinstance(x, (str, int, float)) and str(x)]
    return TavilyExtractResult(url=clean, raw_content=raw, images=images)

