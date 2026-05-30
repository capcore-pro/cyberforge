"""Extraction et injection des blocs CMS depuis content/site.json."""

from __future__ import annotations

from typing import Any

from tools.vitrine.content_schema import VitrineSiteContent

BlockType = str

# (block_key, block_type, dot_path)
EDITABLE_BLOCK_SPECS: list[tuple[str, BlockType, str]] = [
    ("meta.businessName", "text", "meta.businessName"),
    ("meta.tagline", "text", "meta.tagline"),
    ("meta.primaryColor", "color", "meta.primaryColor"),
    ("meta.logoUrl", "image", "meta.logoUrl"),
    ("home.hero.title", "text", "home.hero.title"),
    ("home.hero.subtitle", "text", "home.hero.subtitle"),
    ("home.hero.image.url", "image", "home.hero.image.url"),
    ("home.hero.image.alt", "text", "home.hero.image.alt"),
    ("home.hero.ctaPrimary.label", "text", "home.hero.ctaPrimary.label"),
    ("home.hero.ctaPrimary.href", "url", "home.hero.ctaPrimary.href"),
    ("home.ctaBand.title", "text", "home.ctaBand.title"),
    ("home.ctaBand.text", "text", "home.ctaBand.text"),
    ("home.ctaBand.buttonLabel", "text", "home.ctaBand.buttonLabel"),
    ("contactPage.headline", "text", "contactPage.headline"),
    ("contactPage.subtext", "text", "contactPage.subtext"),
    ("contactPage.sidebar.phone", "text", "contactPage.sidebar.phone"),
    ("contactPage.sidebar.email", "text", "contactPage.sidebar.email"),
    ("contactPage.sidebar.address", "text", "contactPage.sidebar.address"),
    ("footer.description", "text", "footer.description"),
    ("footer.phone", "text", "footer.phone"),
    ("footer.email", "text", "footer.email"),
    ("footer.address", "text", "footer.address"),
    ("footer.legalNote", "text", "footer.legalNote"),
]


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def _normalize_block_value(block_type: BlockType, raw: Any) -> Any:
    if raw is None:
        return None
    if block_type == "image":
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            return {"url": raw, "alt": ""}
    if block_type in ("text", "color", "url"):
        return str(raw) if raw is not None else ""
    return raw


def extract_blocks_from_site_json(raw: str) -> list[dict[str, Any]]:
    """Parse site.json et retourne les blocs éditables."""
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    blocks: list[dict[str, Any]] = []
    for block_key, block_type, path in EDITABLE_BLOCK_SPECS:
        raw_val = _get_path(data, path)
        if raw_val is None:
            continue
        if block_type == "image" and isinstance(raw_val, dict):
            value = {
                "url": raw_val.get("url", ""),
                "alt": raw_val.get("alt", ""),
            }
        else:
            value = _normalize_block_value(block_type, raw_val)
        blocks.append(
            {
                "block_key": block_key,
                "block_type": block_type,
                "value": value,
            }
        )
    return blocks


def apply_blocks_to_site_dict(
    data: dict[str, Any],
    blocks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Applique les blocs CMS (par block_key) sur un dict site.json."""
    spec_by_key = {key: (btype, path) for key, btype, path in EDITABLE_BLOCK_SPECS}
    for block_key, row in blocks.items():
        spec = spec_by_key.get(block_key)
        if not spec:
            continue
        block_type, path = spec
        value = row.get("value")
        normalized = _normalize_block_value(block_type, value)
        if normalized is None:
            continue
        if block_type == "image" and path.endswith(".url"):
            # Injecter url + alt si présents
            parent_path = path.rsplit(".", 1)[0]
            parent = _get_path(data, parent_path)
            if not isinstance(parent, dict):
                parent_obj: dict[str, Any] = {}
                _set_path(data, parent_path, parent_obj)
                parent = parent_obj
            if isinstance(normalized, dict):
                if normalized.get("url"):
                    parent["url"] = normalized["url"]
                if normalized.get("alt") is not None:
                    parent["alt"] = normalized.get("alt") or parent.get("alt", "")
            elif isinstance(normalized, str):
                parent["url"] = normalized
        else:
            _set_path(data, path, normalized)
    return data


def validate_site_content(data: dict[str, Any]) -> dict[str, Any]:
    """Valide via Pydantic ; retourne le dict normalisé."""
    return VitrineSiteContent.model_validate(data).model_dump(by_alias=True)
