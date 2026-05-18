# Architecture CyberForge

CyberForge est une application desktop d’assistance IA pour la cybersécurité. Le dépôt est organisé en couches distinctes : interface utilisateur (Electron), API métier (FastAPI), ressources partagées et persistance.

## Vue d’ensemble

```
┌─────────────────────────────────────────────────────────────┐
│  frontend/ (Electron + React + TypeScript + TailwindCSS)   │
│  ┌─────────────┐    IPC      ┌──────────────────────────┐  │
│  │  Renderer   │ ◄────────► │  Processus principal      │  │
│  │  (React)    │            │  (electron/)              │  │
│  └──────┬──────┘            └──────────────────────────┘  │
└─────────┼──────────────────────────────────────────────────┘
          │ HTTP (VITE_API_BASE_URL)
          ▼
┌─────────────────────────────────────────────────────────────┐
│  backend/ (FastAPI + uvicorn)                              │
│  api/ ── routes HTTP                                         │
│  agents/ ── orchestration des agents IA                    │
│  tools/ ── outils (scan, OSINT, etc.)                      │
└─────────┬───────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────┐     ┌──────────────────────────────────┐
│  database/       │     │  shared/ — types & contrats      │
│  schémas, migrations│  │  communs frontend / backend      │
└──────────────────┘     └──────────────────────────────────┘
```

## Dossiers

| Dossier | Rôle |
|---------|------|
| `frontend/` | Application desktop : UI React, styles Tailwind, processus Electron |
| `backend/` | API REST, agents IA, outils d’exécution |
| `shared/` | Contrats et constantes partagés entre client et serveur |
| `database/` | Schémas SQL, migrations, seeds |
| `docs/` | Documentation technique et guides |

## Flux de données

1. L’utilisateur interagit avec l’interface React dans la fenêtre Electron.
2. Le preload expose une API IPC minimale et sûre (`contextBridge`).
3. Les appels métier passent par HTTP vers le backend (`VITE_API_BASE_URL`).
4. FastAPI route les requêtes vers les modules `api/`, qui délèguent aux `agents/` et `tools/`.
5. La persistance utilise `DATABASE_URL` (jamais codée en dur).

## Sécurité

- **Clés API** : uniquement via variables d’environnement (`.env`, non versionné). Fichier modèle : `.env.example`.
- **Renderer** : `contextIsolation` activé, pas de `nodeIntegration` dans la fenêtre web.
- **Backend** : configuration centralisée dans `config.py` via `pydantic-settings`.

## Démarrage local (résumé)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Copier `.env.example` vers `.env` à la racine du projet et renseigner les valeurs nécessaires.
