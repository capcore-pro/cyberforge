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

## Build & Release

### Prérequis avant npm run release:win
1. Fermer CyberForge complètement (tuer tous les processus Electron)
2. Vérifier GH_TOKEN : `echo $env:GH_TOKEN`
   Si vide : `$env:GH_TOKEN = "ghp_..."` (token repo read/write)
3. Si dist-build verrouillé, utiliser :
   `npx electron-builder --win --publish always --config.directories.output=dist-build-release`

### Après la publication
Vérifier que la release n'est pas en brouillon :
`gh release edit vX.X.X --draft=false`
Ou manuellement sur github.com/capcore-pro/cyberforge/releases

### Checklist release
- [ ] CyberForge-Setup-X.X.X.exe présent
- [ ] CyberForge-Portable-X.X.X.exe présent  
- [ ] latest.yml présent (sha512 cohérent)
- [ ] Release publiée (pas brouillon)
