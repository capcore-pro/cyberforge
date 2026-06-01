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


def _extension_name(prompt: str, slug: str) -> str:
    first = re.sub(r"\s+", " ", (prompt or "").strip())[:60]
    if first:
        return first[0].upper() + first[1:]
    return slug.replace("-", " ").title()


def _permissions_for_prompt(prompt: str) -> list[str]:
    low = (prompt or "").lower()
    perms = ["storage", "activeTab", "scripting"]
    if any(k in low for k in ("onglet", "tabs", "tab ", "historique")):
        perms.append("tabs")
    if any(k in low for k in ("notification", "alerte", "rappel")):
        perms.append("notifications")
    return sorted(set(perms))


def build_extension_files(
    prompt: str,
    *,
    slug: str | None = None,
    primary_color: str = "#4f46e5",
) -> dict[str, str]:
    """
    Génère manifest.json, popup.html, background.js, content.js, README.
    popup.html : 380×500px, toggles ON/OFF, stats, paramètres.
    """
    slug = slug or _slug_from_prompt(prompt)
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


def prepare_extension_preview_html(popup_html: str) -> str:
    """Aperçu iframe = popup seule (380×500), pas une page pleine largeur."""
    from tools.demo_preview_gate import prepare_internal_app_preview_html

    raw = (popup_html or "").strip()
    if not raw:
        return raw
    if 'width: 380px' in raw or 'width:380px' in raw.replace(" ", ""):
        return prepare_internal_app_preview_html(raw)
    return prepare_internal_app_preview_html(raw)
