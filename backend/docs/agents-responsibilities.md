# Directives agents CyberForge — non négociables

## Règle globale

1. **Une responsabilité** par agent.
2. Sortie = `AgentResult` succès avec `data` **ou** `AgentResult` échec avec `code` + `message`.
3. **Interdit** : retourner un livrable vide, un HTML placeholder, ou un succès partiel sans le signaler.

---

## ContentAI (Agent 3)

- **Fait** : remplit chaque placeholder du template avec contenu client réel (nom, ville, services sectoriels, hero accrocheur).
- **Reçoit** : `template_html`, `client_name`, `sector`, `city`, `research_content`, `design_system`.
- **Échoue** : `missing_client_name`, `unfilled_placeholders`, `forbidden_*` (lorem, Service 1, etc.).
- **Ne fait pas** : choisir le template ; modifier la structure HTML ; générer via LLM libre.

## TemplateAI (Agent 2)

- **Fait** : sélectionne et charge le template HTML sectoriel brut (`backend/templates/sectors/`) — placeholders laissés à ContentAI.
- **Templates** : `vitrine_alimentaire`, `vitrine_artisan`, `vitrine_sante`, `vitrine_beaute`, `vitrine_nautisme`, `vitrine_default`.
- **Échoue** : `template_not_found`, `missing_placeholders`, `empty_template`.
- **Ne fait pas** : modifier la loi visuelle DesignSystemAI ; générer du HTML via LLM.

## Ordre pipeline vitrine

`ArchitectAI` → `ResearchAI` (opt.) → `DesignSystemAI` → `TemplateAI` → `ContentAI` → `BuilderAI` → `VisionUI` → `BugHunterAI` → …

Constante : `VITRINE_PIPELINE_ORDER` dans `pipeline_graph.py`.

## DesignSystemAI (Agent 1 — priorité absolue)

- **Fait** : produit le JSON contractuel (`fonts`, `colors`, `spacing`, `border_radius`, `shadows`, `style_keywords`, `google_fonts_url`) **avant** toute génération de code.
- **Couleurs** selon famille sectorielle : alimentaire (crème/brun/doré), marin/sport (bleu/blanc), artisan/BTP (ardoise/orange), santé (vert doux), tech (sombre/néon), beauté (rose/noir), juridique/finance (navy/or).
- **Polices** : artisanal → Playfair+Lato, moderne → Inter+Space Grotesk, élégant → Cormorant+Raleway.
- **Loi visuelle** : JSON transmis à Template, Content, Builder, CoreMind, Vision, BugHunter, Export — aucun agent ne peut dévier.
- **Reçoit** : `sector`, `client_name`, `palette_preference`, `project_type`.
- **Échoue** : `missing_client_name`, `invalid_color`, `incomplete_json` — pipeline stoppé.
- **Ne fait pas** : générer du HTML, du copy long, ou appeler v0/DeepSeek.

## ArchitectAI

- **Fait** : produit `ArchitectPlan` avec `template` ∈ catalogue `core/template_registry.py`.
- **Échoue** : `unknown_template`, `template_project_mismatch` si incohérence.
- **Ne fait pas** : générer du code, appeler v0/DeepSeek.

## ResearchAI

- **Fait** : `ResearchBrief` avec `nom_entreprise`, `secteur`, `ville`, `mots_cles`.
- **Échoue** : `skipped` explicite si clés API absentes (pas de brief vide prétendu enrichi).
- **Ne fait pas** : écrire du HTML.

## BuilderAI (Template-first)

- **Fait** : pour `client_demo` et vitrines HTML, appelle `build_template_first()` **avant** v0/DeepSeek.
- **Échoue** : `missing_slots`, `render_failed` → `fallback_to_coremind=True`.
- **Ne fait pas** : laisser v0 inventer une vitrine from scratch.

## BuilderAI (LLM)

- **Fait** : `real_app`, backends, apps React complexes via v0/DeepSeek.
- **Ne fait pas** : remplacer le catalogue pour une landing client.

## BugHunterAI (vitrine)

- **Bloquant** uniquement : `{{` non remplacé, `<title>` vide/générique, pas de `<h1>`, pas de contact/formulaire.
- **Non bloquant** : scores Playwright, Lighthouse, CSS, lorem (hors placeholders `{{`).
- **Ne fait pas** : bloquer l'export sur un score Lighthouse &lt; 85.

## BugHunterAI (autres démos)

- **Fait** : valider ; injecter identité client sans régénération LLM.
- **Ne fait pas** : boucler sur les mêmes erreurs d'identité (post-traitement d'abord).

## AutoFixAI

- **Fait** : max **2** boucles sur défauts BugHunter bloquants ; puis livrer avec avertissements.
- **Ne fait pas** : boucler sur Playwright/Lighthouse ; régénérer une vitrine entière pour `missing_client_name`.

## Aperçu interne CyberForge

- **Mat** : `?preview=cyberforge_internal` sur l'URL ou HTML sans gate (iframe srcDoc).
- **Tiers** : écran « Démo protégée » + mot de passe (export uniquement).

## ExportAI

- **Fait** : déployer ; appliquer **mot de passe** sur l'URL livrée au client.
- **Ne fait pas** : mettre le gate sur `preview_html` du générateur (voir `strip_password_gate`).
