"""
Pipeline extension_navigateur — Manifest V3, popup Chrome, ZIP (pas template-first).
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from agents.coremind_agent import ProjectType

logger = logging.getLogger(__name__)

_ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "data" / "extension_artifacts"
_EXTENSION_PROVIDER = "cyberforge_extension"
_EXTENSION_MODEL = "extension-mv3-v1"


def is_extension_project_type(plan: Any) -> bool:
    pt = getattr(plan, "project_type", None)
    value = pt.value if hasattr(pt, "value") else str(pt or "")
    if value == ProjectType.EXTENSION_NAVIGATEUR.value:
        return True
    cat = (getattr(plan, "pricing_category", None) or "").strip().lower()
    return cat == "extension_navigateur"


def _slug_from_prompt(prompt: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (prompt or "").lower().strip())[:40]
    return slug.strip("-") or "cyberforge-extension"


_TYPE_PREFIX_RE = re.compile(r"^TYPE:\s*extension_navigateur\s*", re.I)
_NOM_LABEL_RE = re.compile(
    r"nom\s*:\s*['\"]?([^'\"\n,;.]{2,48})['\"]?",
    re.I,
)
_QUOTED_NAME_RE = re.compile(
    r"""['"]([A-Za-zÀ-ÿ][\wÀ-ÿ\-']{1,40})['"]""",
)
_NAME_STOPWORDS = frozenset(
    {
        "extension",
        "chrome",
        "navigateur",
        "type",
        "pour",
        "avec",
        "une",
        "des",
        "les",
        "the",
        "and",
        "qui",
        "dans",
        "sur",
        "manifest",
        "popup",
        "creer",
        "créer",
        "generer",
        "générer",
    }
)


def extract_extension_display_name(prompt: str, *, slug: str = "") -> str:
    """
    Nom court pour titre popup / manifest — jamais le prompt complet.
    Priorité : guillemets ('CleanShop'), « Nom : … », puis mots-clés.
    """
    text = _TYPE_PREFIX_RE.sub("", (prompt or "").strip())
    text = re.sub(r"\s+", " ", text).strip()

    nom_m = _NOM_LABEL_RE.search(text)
    if nom_m:
        label = nom_m.group(1).strip().strip("'\"")
        label = re.split(r"\s*[—–\-]\s*", label, maxsplit=1)[0].strip()
        if 2 <= len(label) <= 48:
            return _format_display_name(label)

    for m in _QUOTED_NAME_RE.finditer(text):
        candidate = m.group(1).strip()
        if len(candidate) < 2:
            continue
        if candidate.lower() in _NAME_STOPWORDS:
            continue
        return _format_display_name(candidate)

    words = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\-]{2,}", text)
    keywords: list[str] = []
    for w in words:
        low = w.lower()
        if low in _NAME_STOPWORDS:
            continue
        if w.isupper() and len(w) <= 5:
            continue
        keywords.append(w)
        if len(keywords) >= 3:
            break

    if keywords:
        return _format_display_name(" ".join(keywords))

    if slug:
        return slug.replace("-", " ").title()
    return "Mon extension"


def _format_display_name(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip())[:48]
    if not s:
        return "Mon extension"
    if re.search(r"[A-Z]", s[1:]):
        return s[0].upper() + s[1:]
    parts = s.split()
    if len(parts) == 1:
        return parts[0][:1].upper() + parts[0][1:].lower()
    return " ".join(p[:1].upper() + p[1:].lower() for p in parts if p)


def _extension_name(prompt: str, slug: str) -> str:
    return extract_extension_display_name(prompt, slug=slug)


def _permissions_for_prompt(prompt: str) -> list[str]:
    low = (prompt or "").lower()
    perms = ["storage", "activeTab", "scripting"]
    if any(k in low for k in ("onglet", "tabs", "tab ", "historique")):
        perms.append("tabs")
    if any(k in low for k in ("notification", "alerte", "rappel")):
        perms.append("notifications")
    return sorted(set(perms))


def resolve_extension_sector_id(brief: dict[str, Any]) -> str:
    """Identifie le preset secteur (ecommerce-helper, productivite, seo-analytics)."""
    raw = " ".join(
        str(brief.get(k) or "")
        for k in ("sector", "sector_id", "id", "prompt", "description")
    ).lower()
    if "ecommerce-helper" in raw or "e-commerce" in raw or "ecommerce helper" in raw:
        return "ecommerce-helper"
    if "productivite" in raw or "productivité" in raw or "productivity" in raw:
        return "productivite"
    if "seo-analytics" in raw or ("seo" in raw and "analytics" in raw):
        return "seo-analytics"
    return "generic"


def _brief_from_args(
    prompt_or_brief: str | dict[str, Any],
    *,
    slug: str | None = None,
    primary_color: str = "#4f46e5",
) -> dict[str, Any]:
    if isinstance(prompt_or_brief, dict):
        brief = dict(prompt_or_brief)
    else:
        brief = {"prompt": str(prompt_or_brief or "")}
    if slug:
        brief.setdefault("slug", slug)
    if primary_color and not brief.get("couleur_primaire"):
        brief.setdefault("couleur_primaire", primary_color)
    prompt = str(brief.get("prompt") or brief.get("description") or "")
    brief.setdefault("prompt", prompt)
    return brief


def build_extension_files(
    prompt_or_brief: str | dict[str, Any],
    *,
    slug: str | None = None,
    primary_color: str = "#4f46e5",
) -> dict[str, str]:
    """
    Génère manifest.json, popup.html, popup.js, background.js, content.js, README.
    Route vers un template secteur si brief["sector"] correspond.
    """
    from tools.extension_sector_templates import (
        build_ecommerce_helper,
        build_productivite,
        build_seo_analytics,
    )

    brief = _brief_from_args(prompt_or_brief, slug=slug, primary_color=primary_color)
    sector_id = resolve_extension_sector_id(brief)
    if sector_id == "ecommerce-helper":
        return build_ecommerce_helper(brief)
    if sector_id == "productivite":
        return build_productivite(brief)
    if sector_id == "seo-analytics":
        return build_seo_analytics(brief)

    prompt = str(brief.get("prompt") or "")
    slug = slug or str(brief.get("slug") or "") or _slug_from_prompt(prompt)
    name = _extension_name(prompt, slug)
    safe_name = html_lib.escape(name)
    description = (prompt.strip()[:200] or "Extension générée par CyberForge").replace(
        "\n", " "
    )
    perms = _permissions_for_prompt(prompt)

    manifest = {
        "manifest_version": 3,
        "name": name,
        "version": "1.0.0",
        "description": description,
        "action": {
            "default_title": name,
            "default_popup": "popup.html",
        },
        "permissions": perms,
        "background": {"service_worker": "background.js"},
    }

    popup_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=380, initial-scale=1" />
  <title>{safe_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 380px;
      min-height: 500px;
      max-height: 500px;
      overflow: hidden;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 13px;
      color: #0f172a;
      background: #f8fafc;
    }}
    .popup {{
      display: flex;
      flex-direction: column;
      height: 500px;
    }}
    .header {{
      padding: 12px 14px;
      background: linear-gradient(135deg, {primary_color}, #1e293b);
      color: #fff;
    }}
    .header h1 {{ font-size: 15px; font-weight: 600; }}
    .header p {{ font-size: 11px; opacity: 0.9; margin-top: 4px; }}
    .body {{ flex: 1; overflow-y: auto; padding: 12px 14px; }}
    .card {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 10px;
    }}
    .card h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 8px; }}
    .row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #f1f5f9;
    }}
    .row:last-child {{ border-bottom: none; }}
    .toggle {{
      position: relative;
      width: 44px;
      height: 24px;
    }}
    .toggle input {{ opacity: 0; width: 0; height: 0; }}
    .slider {{
      position: absolute;
      cursor: pointer;
      inset: 0;
      background: #cbd5e1;
      border-radius: 24px;
      transition: 0.2s;
    }}
    .slider:before {{
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background: white;
      border-radius: 50%;
      transition: 0.2s;
    }}
    input:checked + .slider {{ background: {primary_color}; }}
    input:checked + .slider:before {{ transform: translateX(20px); }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .stat {{
      background: #f1f5f9;
      border-radius: 8px;
      padding: 10px;
      text-align: center;
    }}
    .stat strong {{ display: block; font-size: 18px; color: {primary_color}; }}
    .stat span {{ font-size: 10px; color: #64748b; }}
    .footer {{
      padding: 10px 14px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
    }}
    .footer button {{
      flex: 1;
      padding: 8px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      background: #fff;
      cursor: pointer;
      font: inherit;
      font-size: 12px;
    }}
    .footer button.primary {{
      background: {primary_color};
      color: #fff;
      border-color: {primary_color};
    }}
    #settingsPanel {{ display: none; }}
    #settingsPanel.open {{ display: block; }}
    label.field {{ display: block; font-size: 11px; color: #64748b; margin: 6px 0 4px; }}
    input.text {{ width: 100%; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; }}
  </style>
</head>
<body>
  <div class="popup">
    <header class="header">
      <h1>{safe_name}</h1>
      <p>Extension Chrome — démo CyberForge</p>
    </header>
    <div class="body">
      <div class="card" id="mainPanel">
        <h2>Contrôles</h2>
        <div class="row">
          <span>Extension active</span>
          <label class="toggle"><input type="checkbox" id="toggleMaster" checked /><span class="slider"></span></label>
        </div>
        <div class="row">
          <span>Mode page courante</span>
          <label class="toggle"><input type="checkbox" id="togglePage" checked /><span class="slider"></span></label>
        </div>
        <div class="row">
          <span>Notifications</span>
          <label class="toggle"><input type="checkbox" id="toggleNotif" /><span class="slider"></span></label>
        </div>
      </div>
      <div class="card">
        <h2>Statistiques</h2>
        <div class="stats">
          <div class="stat"><strong id="statActions">0</strong><span>Actions</span></div>
          <div class="stat"><strong id="statPages">0</strong><span>Pages</span></div>
        </div>
      </div>
      <div class="card" id="settingsPanel">
        <h2>Paramètres</h2>
        <label class="field" for="optLabel">Libellé affiché</label>
        <input class="text" id="optLabel" type="text" value="{safe_name}" />
        <label class="field" for="optDelay">Délai (ms)</label>
        <input class="text" id="optDelay" type="number" value="300" min="0" />
      </div>
    </div>
    <footer class="footer">
      <button type="button" id="btnSettings">Paramètres</button>
      <button type="button" class="primary" id="btnApply">Appliquer</button>
    </footer>
  </div>
  <script src="popup.js"></script>
</body>
</html>
"""

    popup_js = """const KEYS = {
  master: "cf_master_enabled",
  page: "cf_page_enabled",
  notif: "cf_notif_enabled",
  actions: "cf_stat_actions",
  pages: "cf_stat_pages",
  label: "cf_opt_label",
  delay: "cf_opt_delay",
};

async function load() {
  const data = await chrome.storage.local.get({
    [KEYS.master]: true,
    [KEYS.page]: true,
    [KEYS.notif]: false,
    [KEYS.actions]: 0,
    [KEYS.pages]: 0,
    [KEYS.label]: "",
    [KEYS.delay]: 300,
  });
  document.getElementById("toggleMaster").checked = data[KEYS.master];
  document.getElementById("togglePage").checked = data[KEYS.page];
  document.getElementById("toggleNotif").checked = data[KEYS.notif];
  document.getElementById("statActions").textContent = String(data[KEYS.actions]);
  document.getElementById("statPages").textContent = String(data[KEYS.pages]);
  if (data[KEYS.label]) {
    document.getElementById("optLabel").value = data[KEYS.label];
  }
  document.getElementById("optDelay").value = String(data[KEYS.delay]);
  syncToBackground();
}

async function save(partial) {
  await chrome.storage.local.set(partial);
  syncToBackground();
}

function syncToBackground() {
  chrome.runtime.sendMessage({ type: "cf_sync_state" }).catch(() => {});
}

document.getElementById("toggleMaster").addEventListener("change", (e) => {
  save({ [KEYS.master]: e.target.checked });
});
document.getElementById("togglePage").addEventListener("change", (e) => {
  save({ [KEYS.page]: e.target.checked });
});
document.getElementById("toggleNotif").addEventListener("change", (e) => {
  save({ [KEYS.notif]: e.target.checked });
});
document.getElementById("btnSettings").addEventListener("click", () => {
  document.getElementById("settingsPanel").classList.toggle("open");
});
document.getElementById("btnApply").addEventListener("click", async () => {
  const label = document.getElementById("optLabel").value.trim();
  const delay = parseInt(document.getElementById("optDelay").value, 10) || 0;
  await save({ [KEYS.label]: label, [KEYS.delay]: delay });
  const actions = (await chrome.storage.local.get({ [KEYS.actions]: 0 }))[KEYS.actions];
  await save({ [KEYS.actions]: actions + 1 });
  document.getElementById("statActions").textContent = String(actions + 1);
});

load();
"""

    background_js = """const DEFAULTS = {
  cf_master_enabled: true,
  cf_page_enabled: true,
  cf_notif_enabled: false,
  cf_stat_actions: 0,
  cf_stat_pages: 0,
};

chrome.runtime.onInstalled.addListener(async () => {
  const cur = await chrome.storage.local.get(DEFAULTS);
  await chrome.storage.local.set({ ...DEFAULTS, ...cur });
  console.log("[CyberForge] extension installed");
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "cf_sync_state") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0] && tabs[0].id;
      if (tabId != null) {
        chrome.tabs.sendMessage(tabId, { type: "cf_apply_state" }).catch(() => {});
      }
      sendResponse({ ok: true });
    });
    return true;
  }
  if (msg && msg.type === "cf_page_visit") {
    chrome.storage.local.get({ cf_stat_pages: 0 }, (data) => {
      chrome.storage.local.set({ cf_stat_pages: (data.cf_stat_pages || 0) + 1 });
    });
    sendResponse({ ok: true });
  }
  return false;
});
"""

    content_js = """async function readState() {
  return chrome.storage.local.get({
    cf_master_enabled: true,
    cf_page_enabled: true,
    cf_notif_enabled: false,
    cf_opt_delay: 300,
  });
}

function applyVisual(enabled) {
  if (!enabled) {
    document.documentElement.style.filter = "";
    document.documentElement.removeAttribute("data-cf-extension");
    return;
  }
  document.documentElement.setAttribute("data-cf-extension", "on");
  document.documentElement.style.outline = "2px solid rgba(79, 70, 229, 0.35)";
}

async function applyFromStorage() {
  const state = await readState();
  const on = Boolean(state.cf_master_enabled && state.cf_page_enabled);
  applyVisual(on);
  if (on) {
    chrome.runtime.sendMessage({ type: "cf_page_visit" }).catch(() => {});
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "cf_apply_state") {
    applyFromStorage();
  }
});

applyFromStorage();
"""

    readme = f"""# {name}

Extension Chrome Manifest V3 générée par CyberForge.

## Installation
1. Ouvrir `chrome://extensions`
2. Activer **Mode développeur**
3. **Charger l'extension non empaquetée**
4. Sélectionner ce dossier (fichiers dézippés)

## Fichiers
- `manifest.json` — configuration MV3
- `popup.html` / `popup.js` — interface popup 380×500
- `background.js` — service worker
- `content.js` — script injecté sur les pages
"""

    return {
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "popup.html": popup_html,
        "popup.js": popup_js,
        "background.js": background_js,
        "content.js": content_js,
        "README.md": readme,
    }


def build_extension_zip(files: dict[str, str]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            if path and content is not None:
                zf.writestr(path.lstrip("/"), content)
    return buf.getvalue()


def save_extension_zip_artifact(project_id: str, zip_bytes: bytes) -> Path:
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", project_id)[:80] or "extension"
    path = _ARTIFACT_DIR / f"{safe}.zip"
    path.write_bytes(zip_bytes)
    return path


def extension_artifact_download_path(project_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", project_id)[:80] or "extension"
    return f"/api/pipeline/extension-artifact/{safe}"


def build_extension_export_manifest(
    *,
    project_id: str,
    project_type_label: str,
    files: list[str],
    zip_bytes: int,
    download_url: str,
) -> dict[str, Any]:
    """
    Métadonnées export extension — pas de domaine, env cloud ni deploy manifest universel.
    """
    return {
        "version": "1",
        "artifact_type": "chrome_extension_zip",
        "project_name": project_id,
        "project_type": ProjectType.EXTENSION_NAVIGATEUR.value,
        "project_type_label": project_type_label,
        "provider": "zip",
        "files": sorted(set(files)),
        "artifact_bytes": zip_bytes,
        "download_url": download_url,
    }


_EXTENSION_PREVIEW_FRAME_CSS = """
<style id="cf-extension-preview-frame">
html, body {
  width: auto !important;
  min-height: 100vh;
  max-height: none !important;
  overflow: auto !important;
  background: #e2e8f0;
}
.cf-extension-preview-shell {
  max-width: 380px;
  margin: 20px auto;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}
.cf-extension-preview-shell .popup {
  width: 380px;
  max-width: 100%;
}
</style>"""

_EXTENSION_PREVIEW_CHROME_SHIM = """<script id="cf-extension-preview-shim">
(function () {
  if (window.chrome && window.chrome.storage && window.chrome.storage.local) return;
  var data = {
    cf_master_enabled: true,
    cf_page_enabled: true,
    cf_notif_enabled: false,
    cf_stat_actions: 0,
    cf_stat_pages: 0,
    cf_opt_label: "",
    cf_opt_delay: 300
  };
  function resolveKeys(keys) {
    if (keys == null) return {};
    var out = {};
    if (typeof keys === "string") {
      out[keys] = data[keys];
      return out;
    }
    if (Array.isArray(keys)) {
      keys.forEach(function (k) { out[k] = data[k]; });
      return out;
    }
    if (typeof keys === "object") {
      Object.keys(keys).forEach(function (k) {
        out[k] = Object.prototype.hasOwnProperty.call(data, k) ? data[k] : keys[k];
      });
    }
    return out;
  }
  window.chrome = {
    storage: {
      local: {
        get: function (keys) { return Promise.resolve(resolveKeys(keys)); },
        set: function (items) {
          Object.assign(data, items || {});
          return Promise.resolve();
        }
      }
    },
    runtime: { sendMessage: function () { return Promise.resolve(); } }
  };
})();
</script>"""


def _normalize_popup_path(path: str) -> str:
    return (path or "").strip().replace("\\", "/").lower()


def extract_extension_popup_html(
    *,
    extension_files: dict[str, str] | None = None,
    generation: Any = None,
    assembled_html: str | None = None,
    preview_html: str | None = None,
) -> tuple[str, str]:
    """
    Retourne (popup.html, popup.js) depuis extension_files, generation.files ou fallbacks.
    """
    popup = ""
    popup_js = ""

    def absorb_files(files: dict[str, str]) -> None:
        nonlocal popup, popup_js
        for path, content in files.items():
            norm = _normalize_popup_path(path)
            if norm.endswith("popup.html") and content:
                popup = str(content).strip()
            elif norm.endswith("popup.js") and content:
                popup_js = str(content).strip()

    if extension_files:
        absorb_files(extension_files)

    if not popup:
        for f in getattr(generation, "files", None) or []:
            path = _normalize_popup_path(str(getattr(f, "path", "") or ""))
            content = str(getattr(f, "content", "") or "").strip()
            if path.endswith("popup.html") and content:
                popup = content
            elif path.endswith("popup.js") and content:
                popup_js = content

    for candidate in (assembled_html, preview_html, getattr(generation, "code", None)):
        text = str(candidate or "").strip()
        if not text:
            continue
        low = text.lower()
        if "<!doctype" in low or "<html" in low:
            popup = text
            break

    return popup, popup_js


def _apply_extension_display_name_to_html(html: str, name: str) -> str:
    safe = html_lib.escape(name)
    html = re.sub(r"<title>[^<]*</title>", f"<title>{safe}</title>", html, count=1, flags=re.I)
    html = re.sub(r"(<h1[^>]*>)[^<]*(</h1>)", rf"\1{safe}\2", html, count=1, flags=re.I)
    html = re.sub(
        r'(<input[^>]*\bid=["\']optLabel["\'][^>]*\bvalue=["\'])[^"\']*(["\'])',
        rf'\1{safe}\2',
        html,
        count=1,
        flags=re.I,
    )
    return html


def _wrap_popup_preview_shell(html: str) -> str:
    if "cf-extension-preview-shell" in html:
        return html

    if 'id="cf-extension-preview-frame"' not in html:
        if re.search(r"</head>", html, re.I):
            html = re.sub(
                r"(</head>)",
                _EXTENSION_PREVIEW_FRAME_CSS + r"\1",
                html,
                count=1,
                flags=re.I,
            )
        else:
            html = _EXTENSION_PREVIEW_FRAME_CSS + html

    body_m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    if not body_m:
        return html
    inner = body_m.group(1).strip()
    if not inner.startswith('<div class="cf-extension-preview-shell"'):
        wrapped = f'<div class="cf-extension-preview-shell">{inner}</div>'
        html = (
            html[: body_m.start(1)]
            + wrapped
            + html[body_m.end(1) :]
        )
    return html


def prepare_extension_preview_html(
    popup_html: str,
    *,
    popup_js: str | None = None,
    prompt: str | None = None,
) -> str:
    """
    Aperçu iframe CyberForge : popup centrée 380px, JS inline, mock chrome.*.
    """
    from tools.demo_preview_gate import inject_internal_preview_meta
    from tools.html_markdown import strip_markdown_code_fences

    html = strip_markdown_code_fences((popup_html or "").strip())
    if not html:
        return html

    if prompt is not None:
        display_name = extract_extension_display_name(prompt)
        html = _apply_extension_display_name_to_html(html, display_name)

    js = (popup_js or "").strip()
    if js:
        html = re.sub(
            r'<script\s+src=["\']popup\.js["\']\s*></script>',
            f"<script>\n{js}\n</script>",
            html,
            count=1,
            flags=re.I,
        )

    if 'id="cf-extension-preview-shim"' not in html:
        if re.search(r"<head\b", html, re.I):
            html = re.sub(
                r"(<head[^>]*>)",
                r"\1\n" + _EXTENSION_PREVIEW_CHROME_SHIM,
                html,
                count=1,
                flags=re.I,
            )
        else:
            html = _EXTENSION_PREVIEW_CHROME_SHIM + html

    html = _wrap_popup_preview_shell(html)
    return inject_internal_preview_meta(html)
