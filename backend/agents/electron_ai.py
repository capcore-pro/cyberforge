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
        "instructions_build.md": "..."
      },
      "summary": "..."
    }
"""

from __future__ import annotations

import json
import re
from typing import Any


def _kebab_case(text: str, fallback: str = "cyberforge-desktop") -> str:
    raw = (text or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw)
    collapsed = re.sub(r"-{2,}", "-", normalized).strip("-")
    return collapsed or fallback


def _guess_app_name(project_description: str) -> str:
    for line in (project_description or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:80]
    return "CyberForge Desktop"


def build_electron_files(
    project_description: str,
    *,
    app_name: str | None = None,
) -> dict[str, str]:
    """Génère les fichiers Electron complets (templates déterministes)."""
    name = (app_name or _guess_app_name(project_description)).strip() or "CyberForge Desktop"
    slug = _kebab_case(name)
    description = (project_description or name).strip()[:500]
    safe_name = name.replace('"', "'")
    safe_description = description.replace('"', "'")

    main_js = f"""const {{ app, BrowserWindow, ipcMain, shell }} = require('electron')
const path = require('path')
const fs = require('fs')

let mainWindow

function createWindow() {{
  mainWindow = new BrowserWindow({{
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {{
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }},
    titleBarStyle: 'default',
    title: '{safe_name}',
    icon: path.join(__dirname, 'assets', 'icon.png')
  }})
  mainWindow.loadFile('index.html')
  mainWindow.setMenuBarVisibility(false)
}}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {{
  if (process.platform !== 'darwin')
    app.quit()
}})
"""

    preload_js = f"""const {{ contextBridge, ipcRenderer }} = require('electron')
const fs = require('fs')
const path = require('path')

const dataPath = path.join(
  process.env.APPDATA || '.',
  '{slug}', 'data.json'
)

contextBridge.exposeInMainWorld('app', {{
  getData: () => {{
    try {{
      if (fs.existsSync(dataPath))
        return JSON.parse(fs.readFileSync(dataPath, 'utf8'))
      return {{}}
    }} catch {{ return {{}} }}
  }},
  setData: (data) => {{
    const dir = path.dirname(dataPath)
    if (!fs.existsSync(dir))
      fs.mkdirSync(dir, {{ recursive: true }})
    fs.writeFileSync(
      dataPath,
      JSON.stringify(data, null, 2)
    )
  }},
  appVersion: process.env.npm_package_version || '1.0.0'
}})
"""

    package_json = json.dumps(
        {
            "name": slug,
            "version": "1.0.0",
            "description": safe_description,
            "main": "main.js",
            "scripts": {
                "start": "electron .",
                "build": "electron-builder --win --x64",
                "build:win": "electron-builder --win --x64",
                "build-portable": "electron-builder --win portable",
            },
            "build": {
                "appId": f"pro.capcore.{slug}",
                "productName": safe_name,
                "directories": {"output": "dist"},
                "win": {
                    "target": [
                        {"target": "nsis", "arch": ["x64"]},
                        {"target": "portable", "arch": ["x64"]},
                    ],
                    "icon": "assets/icon.ico",
                },
                "nsis": {
                    "oneClick": False,
                    "allowToChangeInstallationDirectory": True,
                    "installerIcon": "assets/icon.ico",
                    "uninstallerIcon": "assets/icon.ico",
                    "createDesktopShortcut": True,
                    "createStartMenuShortcut": True,
                },
            },
            "dependencies": {},
            "devDependencies": {
                "electron": "^28.0.0",
                "electron-builder": "^24.0.0",
            },
        },
        ensure_ascii=False,
        indent=2,
    )

    instructions = f"""# Build {safe_name} — Instructions

## Prérequis
- Node.js 18+ installé
- npm install (dans ce dossier)

## Développement (test rapide)
npm start

## Build .exe Windows
npm run build

Le .exe sera dans dist/

## Build portable (sans installation)
npm run build-portable

## Livraison au client
Envoyer le fichier .exe ou le dossier portable par email ou
lien de téléchargement.
"""

    return {
        "main.js": main_js,
        "preload.js": preload_js,
        "package.json": package_json,
        "instructions_build.md": instructions,
    }


async def run(
    project_description: str,
    assembled_html: str,
    database_schema: dict,
) -> dict[str, Any]:
    """Génère les fichiers Electron pour empaqueter le HTML en application Windows."""
    _ = assembled_html
    _ = database_schema
    desc = (project_description or "").strip()
    files = build_electron_files(desc)
    app_name = _guess_app_name(desc)
    return {
        "files": files,
        "summary": f"Package Electron généré pour {app_name}.",
    }
