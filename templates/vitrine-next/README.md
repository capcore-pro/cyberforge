# Template vitrine Next.js — CyberForge Phase 4.2a

Site vitrine multi-pages (App Router) alimenté par `content/site.json`.

## Pages

- `/` — Accueil (hero, services, témoignages, CTA)
- `/services` — Prestations détaillées
- `/contact` — Formulaire (API stub `/api/contact`)

## Développement local

```bash
cd templates/vitrine-next
npm install
npm run dev
```

Ouvrir http://localhost:3000

## Contenu

Modifier `content/site.json` (exemple : plombier à Rouen). Les couleurs primaires sont injectées via `meta.primaryColor`.

## Stack

- Next.js 14 (App Router)
- Tailwind CSS + composants shadcn/ui
- Images Unsplash (URLs dans le JSON)
