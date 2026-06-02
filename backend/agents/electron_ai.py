"""
ElectronAI — génère les fichiers nécessaires pour empaqueter une app HTML en .exe (Windows).

Interface:
    async def run(project_description: str, assembled_html: str, database_schema: dict) -> dict

Retour:
    {
      "files": {
        "main.js": "...",
        "preload.js": "...",
        "package.json": "...",
        "installer_config.json": "..."
      },
      "summary": "..."
    }
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

import anthropic  # noqa: E402

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 6000


SYSTEM_PROMPT = """
Tu es ElectronAI, expert Electron.js pour applications desktop Windows.
Génère les fichiers nécessaires pour empaqueter une app HTML en .exe installable.

Fichiers à générer :

main.js — fichier principal Electron :
- BrowserWindow 1200x800, resizable, frame natif Windows
- Charger index.html depuis le dossier app/
- Menu natif : Fichier (Nouveau, Enregistrer, Imprimer, Quitter), Aide (À propos)
- IPC handlers : save-data, load-data, print-page
- Pas de nodeIntegration, contextIsolation: true
- Icône : app/icon.ico

preload.js — bridge sécurisé :
- Exposer via contextBridge.exposeInMainWorld('electronAPI', {...})
- saveData(key, data), loadData(key), printPage()

package.json — configuration electron-builder :
- name en kebab-case depuis le nom du projet
- version 1.0.0
- scripts : start, build
- electron-builder config :
  - target: nsis (installateur Windows)
  - icon: app/icon.ico
  - outputDirectory: dist/
  - oneClick: false, allowDirChange: true
  - languages: French

installer_config.json — métadonnées :
{
  "app_name": "...",
  "version": "1.0.0",
  "target": "windows",
  "installer_type": "nsis",
  "output": "dist/"
}

Retourner UNIQUEMENT un JSON valide sans markdown :
{
  "files": {
    "main.js": "...",
    "preload.js": "...",
    "package.json": "...",
    "installer_config.json": "..."
  },
  "summary": "Description courte"
}
""".strip()


def _kebab_case(text: str, fallback: str = "cyberforge-desktop") -> str:
    raw = (text or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    return raw or fallback


def _guess_app_name(project_description: str) -> str:
    first = (project_description or "").strip().splitlines()[0:1]
    name = first[0].strip() if first else ""
    # coupe si la première ligne est énorme
    return (name[:60] or "CyberForge Desktop").strip()


def _fallback_files(project_description: str) -> dict[str, str]:
    app_name = _guess_app_name(project_description)
    pkg_name = _kebab_case(app_name)

    main_js = r"""const { app, BrowserWindow, Menu, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    resizable: true,
    frame: true,
    icon: path.join(__dirname, "app", "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.loadFile(path.join(__dirname, "app", "index.html"));

  const template = [
    {
      label: "Fichier",
      submenu: [
        { label: "Nouveau", click: () => win.webContents.send("menu:new") },
        { label: "Enregistrer", click: () => win.webContents.send("menu:save") },
        { label: "Imprimer", click: () => win.webContents.print({}) },
        { type: "separator" },
        { label: "Quitter", role: "quit" },
      ],
    },
    {
      label: "Aide",
      submenu: [
        {
          label: "À propos",
          click: async () => {
            await dialog.showMessageBox(win, {
              type: "info",
              title: "À propos",
              message: app.getName(),
              detail: `Version ${app.getVersion()}`,
            });
          },
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

ipcMain.handle("save-data", async (_event, key, data) => {
  const userData = app.getPath("userData");
  const filePath = path.join(userData, `${String(key)}.json`);
  fs.writeFileSync(filePath, JSON.stringify(data ?? null, null, 2), "utf-8");
  return { ok: true, path: filePath };
});

ipcMain.handle("load-data", async (_event, key) => {
  const userData = app.getPath("userData");
  const filePath = path.join(userData, `${String(key)}.json`);
  if (!fs.existsSync(filePath)) return { ok: true, data: null };
  const raw = fs.readFileSync(filePath, "utf-8");
  return { ok: true, data: JSON.parse(raw) };
});

ipcMain.handle("print-page", async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return { ok: false };
  win.webContents.print({});
  return { ok: true };
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
"""

    preload_js = r"""const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  saveData: (key, data) => ipcRenderer.invoke("save-data", key, data),
  loadData: (key) => ipcRenderer.invoke("load-data", key),
  printPage: () => ipcRenderer.invoke("print-page"),
});
"""

    package_json = f"""{{
  "name": "{pkg_name}",
  "version": "1.0.0",
  "private": true,
  "main": "main.js",
  "scripts": {{
    "start": "electron .",
    "build": "electron-builder --win nsis"
  }},
  "devDependencies": {{
    "electron": "^31.3.1",
    "electron-builder": "^24.13.3"
  }},
  "build": {{
    "appId": "pro.capcore.cyberforge.desktop",
    "productName": "{app_name.replace('"', '')}",
    "directories": {{
      "output": "dist"
    }},
    "win": {{
      "target": ["nsis"],
      "icon": "app/icon.ico"
    }},
    "nsis": {{
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "language": "1036"
    }}
  }}
}}
"""

    installer_config = f"""{{
  "app_name": "{app_name.replace('"', '')}",
  "version": "1.0.0",
  "target": "windows",
  "installer_type": "nsis",
  "output": "dist/"
}}
"""

    return {
        "main.js": main_js,
        "preload.js": preload_js,
        "package.json": package_json,
        "installer_config.json": installer_config,
    }


async def _call_claude(system_prompt: str, user_prompt: str):
    def _do_call():
        return client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

    return await asyncio.to_thread(_do_call)


async def run(project_description: str, assembled_html: str, database_schema: dict) -> dict:
    import json as json_module

    desc = (project_description or "").strip()
    html = (assembled_html or "").strip()
    schema = database_schema if isinstance(database_schema, dict) else {}

    user_prompt = (
        "## Description du projet\n"
        f"{desc}\n\n"
        "## assembled_html (extrait)\n"
        f"{html[:8000]}\n\n"
        "## database_schema (JSON)\n"
        f"{json_module.dumps(schema, ensure_ascii=False)[:8000]}"
    ).strip()

    try:
        response = await _call_claude(SYSTEM_PROMPT, user_prompt)
        raw_text = response.content[0].text

        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Aucun JSON trouvé")
        json_str = cleaned[start : end + 1]

        parsed = json_module.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError("JSON racine invalide")
        if "files" not in parsed or "summary" not in parsed:
            raise ValueError("JSON incomplet — clés manquantes")

        files = parsed.get("files")
        if not isinstance(files, dict):
            raise ValueError("Champ files invalide")

        out_files: dict[str, str] = {}
        for k in ("main.js", "preload.js", "package.json", "installer_config.json"):
            v = files.get(k)
            if isinstance(v, str) and v.strip():
                out_files[k] = v
        if not out_files:
            raise ValueError("Aucun fichier généré")

        return {
            "files": out_files,
            "summary": str(parsed.get("summary") or "").strip() or "Fichiers Electron générés.",
        }
    except Exception:
        return {
            "files": _fallback_files(desc),
            "summary": "Fallback ElectronAI — fichiers minimaux générés.",
        }

