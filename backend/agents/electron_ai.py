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


def send_update_notification_email(
    client_email: str,
    client_name: str,
    app_name: str,
    version: str,
    download_url: str,
    notes_maj: str = "",
) -> bool:
    """Envoie un email de notification de mise à jour .exe au client."""
    import httpx
    import os
    from datetime import datetime

    now = datetime.now().strftime("%d/%m/%Y")
    notes_html = f"""
    <div style="background-color:#0f0f13;border:1px solid #374151;border-left:4px solid #f59e0b;
                border-radius:8px;padding:16px 20px;margin:24px 0;">
      <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;font-weight:600;">
        Notes de mise à jour
      </p>
      <p style="color:#cbd5e1;font-size:14px;margin:0;line-height:1.6;">
        {notes_maj}
      </p>
    </div>
    """ if notes_maj else ""

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#0f0f13;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f13;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                       padding:40px 40px 30px;border-radius:12px 12px 0 0;text-align:center;">
              <div style="font-size:28px;font-weight:900;letter-spacing:2px;color:#f59e0b;">
                ⚡ CAPCORE
              </div>
              <div style="color:#94a3b8;font-size:12px;letter-spacing:3px;margin-top:4px;">
                STUDIO DIGITAL
              </div>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="background-color:#1a1a2e;padding:40px;">

              <!-- Icone update -->
              <div style="text-align:center;margin-bottom:24px;">
                <div style="display:inline-block;width:64px;height:64px;
                            background:linear-gradient(135deg,#1e3a5f,#1e40af);
                            border-radius:50%;line-height:64px;font-size:28px;">
                  🔄
                </div>
              </div>

              <h1 style="color:#f1f5f9;font-size:22px;font-weight:700;
                         text-align:center;margin:0 0 8px;">
                Mise à jour disponible
              </h1>
              <p style="color:#94a3b8;font-size:14px;text-align:center;margin:0 0 32px;">
                {app_name} — version {version} — {now}
              </p>

              <p style="color:#cbd5e1;font-size:15px;line-height:1.6;margin:0 0 16px;">
                Bonjour {client_name},
              </p>
              <p style="color:#cbd5e1;font-size:15px;line-height:1.6;margin:0 0 24px;">
                Une nouvelle version de votre logiciel
                <strong style="color:#f1f5f9;">{app_name}</strong>
                est disponible au téléchargement.
              </p>

              {notes_html}

              <!-- Bouton CTA -->
              <div style="text-align:center;margin:32px 0;">
                <a href="{download_url}" target="_blank"
                   style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);
                          color:#0f0f13;font-weight:700;font-size:15px;padding:14px 36px;
                          border-radius:8px;text-decoration:none;letter-spacing:0.5px;">
                  Télécharger la version {version} →
                </a>
              </div>

              <!-- Info version -->
              <div style="background-color:#0f0f13;border:1px solid #374151;
                          border-radius:8px;padding:16px 20px;margin:0 0 24px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="color:#94a3b8;font-size:13px;">Logiciel</td>
                    <td style="color:#f1f5f9;font-size:13px;text-align:right;
                               font-weight:600;">{app_name}</td>
                  </tr>
                  <tr>
                    <td style="color:#94a3b8;font-size:13px;padding-top:8px;">
                      Nouvelle version
                    </td>
                    <td style="color:#f59e0b;font-size:13px;text-align:right;
                               font-weight:600;padding-top:8px;">v{version}</td>
                  </tr>
                </table>
              </div>

              <p style="color:#64748b;font-size:13px;line-height:1.6;margin:0;">
                Si vous avez des questions sur cette mise à jour, répondez simplement
                à cet email.
              </p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#0f0f13;padding:24px 40px;
                       border-radius:0 0 12px 12px;border-top:1px solid #1e293b;
                       text-align:center;">
              <p style="color:#475569;font-size:12px;margin:0 0 4px;">
                Mat · CapCore Studio Digital
              </p>
              <p style="color:#334155;font-size:11px;margin:0;">
                Votre partenaire digital
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    from config import get_settings, plain_secret_str

    settings = get_settings()
    sender_email = (settings.brevo_sender_email or "").strip() or "contact@capcore.pro"
    sender_name = (settings.brevo_sender_name or "").strip() or "Mat · CapCore Studio Digital"

    brevo_api_key = plain_secret_str(settings.brevo_api_key) or os.getenv(
        "BREVO_API_KEY", ""
    )
    if not brevo_api_key:
        print("[ElectronUpdaterAI] BREVO_API_KEY manquante")
        return False

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
                json={
                    "sender": {
                        "name": sender_name,
                        "email": sender_email,
                    },
                    "to": [{"email": client_email, "name": client_name}],
                    "subject": f"🔄 Mise à jour {app_name} — version {version} disponible",
                    "htmlContent": html_content,
                },
            )
            return response.status_code == 201
    except Exception as e:
        print(f"[ElectronUpdaterAI] Erreur envoi email : {e}")
        return False
