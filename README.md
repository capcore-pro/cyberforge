# CyberForge

Logiciel desktop IA pour la cybersécurité — **Electron**, **React**, **TypeScript**, **TailwindCSS** (frontend) et **FastAPI** (backend).

## Structure

```
cyberforge/
├── frontend/     # Application Electron + React
├── backend/      # API FastAPI, agents, outils
├── shared/       # Types et constantes partagés
├── database/     # Schémas et migrations
└── docs/         # Documentation (voir ARCHITECTURE.md)
```

## Démarrage rapide

1. Copier `.env.example` vers `.env` à la racine et renseigner les variables (sans committer `.env`).
2. **Backend** : `cd backend` → créer un venv → `pip install -r requirements.txt` → `uvicorn main:app --reload`
3. **Frontend** : `cd frontend` → `npm install` → `npm run dev`

Documentation détaillée : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
