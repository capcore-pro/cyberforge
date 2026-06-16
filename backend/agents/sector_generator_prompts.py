"""
Instructions GeneratorAI par secteur — pages, CTA, vocabulaire et requêtes Pexels.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

SectorKind = Literal["vitrine", "reservation", "ecommerce", "app_web", "crm"]


@dataclass(frozen=True)
class SectorGeneratorProfile:
    id: str
    kind: SectorKind
    """Groupes OR : chaque groupe est un AND de sous-chaînes (secteur ou libellé wizard)."""
    matcher_groups: tuple[tuple[str, ...], ...]
    instructions: str


def _normalize_sector_text(text: str) -> str:
    folded = unicodedata.normalize("NFD", (text or "").strip().lower())
    without_accents = "".join(
        ch for ch in folded if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents)


def _extract_sector_from_brief(brief: dict[str, Any]) -> str:
    sector = str(brief.get("sector") or "").strip()
    if sector:
        return sector
    prompt = str(brief.get("prompt") or "")
    match = re.search(
        r"(?im)^\s*Secteur\s*:\s*(.+)$",
        prompt,
    )
    if match:
        return match.group(1).strip()
    return ""


def _brief_kind(brief: dict[str, Any]) -> SectorKind | None:
    b = brief or {}
    prompt = str(b.get("prompt") or "")
    for key in ("project_type", "generation_mode"):
        val = str(b.get(key) or "").strip().lower().replace("-", "_")
        if val == "crm":
            return "crm"
        if val in ("application_web", "real_app"):
            return "app_web"
        if val == "site_reservation":
            return "reservation"
        if val in ("ecommerce", "saas_dashboard"):
            return "ecommerce"
    if re.search(r"(?m)^TYPE:\s*crm\b", prompt, re.I):
        return "crm"
    if re.search(r"(?m)^TYPE:\s*application_web\b", prompt, re.I):
        return "app_web"
    if re.search(r"(?m)^TYPE:\s*site_reservation\b", prompt, re.I):
        return "reservation"
    if re.search(r"(?m)^TYPE:\s*ecommerce\b", prompt, re.I):
        return "ecommerce"
    return "vitrine"


def _profile_matches(sector_norm: str, profile: SectorGeneratorProfile) -> bool:
    if not sector_norm:
        return False
    for group in profile.matcher_groups:
        if len(group) == 1:
            if group[0] in sector_norm:
                return True
        elif all(token in sector_norm for token in group):
            return True
    return False


# Ordre : motifs les plus spécifiques en premier
SECTOR_GENERATOR_PROFILES: tuple[SectorGeneratorProfile, ...] = (
    # —— Réservation (7) ——
    SectorGeneratorProfile(
        id="camping-plein-air",
        kind="reservation",
        matcher_groups=(("camping", "plein air"), ("camping",)),
        instructions="""SECTEUR : Camping & Plein air (réservation)
- Vocabulaire : mobil-home, chalet, emplacement tente, piscine, animations, nature, séjour famille
- Hero slider : sous-titres nature / piscine / aventure / souvenirs
- Hébergements : mobil-home, chalet, emplacement tente (cards avec prix/nuit)
- Calendrier interactif + formulaire réservation avec calcul nuits × prix
- CTA principal : « Réserver mon séjour »
- Photos Pexels (alt descriptifs) : « mobile home camping », « wooden chalet forest », « family campsite pool », « camping tent nature »""",
    ),
    SectorGeneratorProfile(
        id="hotel-hebergement",
        kind="reservation",
        matcher_groups=(("hotel", "hebergement"),),
        instructions="""SECTEUR : Hôtel & Hébergement (réservation)
- Vocabulaire : chambre, suite, nuitée, petit-déjeuner, spa, séminaire, accueil 24h
- Hero slider : confort, élégance, bien-être, escapade
- Hébergements : chambres avec photos, capacité, prix par nuit
- Calendrier + formulaire : dates arrivée/départ, type de chambre, nombre de personnes
- CTA : « Réserver une chambre »
- Pexels alt : « luxury hotel room », « hotel suite interior », « hotel breakfast buffet », « boutique hotel facade »""",
    ),
    SectorGeneratorProfile(
        id="gite-location",
        kind="reservation",
        matcher_groups=(("gite", "location"), ("gite", "saisonniere")),
        instructions="""SECTEUR : Gîte & Location saisonnière (réservation)
- Vocabulaire : gîte, maison de vacances, week-end, semaine, ménage, authenticité
- Section présentation du gîte (photos intérieur/extérieur)
- Calendrier disponibilités + formulaire réservation
- Bloc conditions (arrivée 16h, départ 10h, caution)
- CTA : « Réserver le gîte »
- Pexels alt : « cozy holiday cottage », « vacation rental living room », « countryside gite france », « family holiday home »""",
    ),
    SectorGeneratorProfile(
        id="restaurant-table",
        kind="reservation",
        matcher_groups=(
            ("reservation", "table"),
            ("restauration", "reservation"),
            ("reservation table",),
        ),
        instructions="""SECTEUR : Restaurant — réservation table (réservation)
- Vocabulaire : table, couverts, menu, déjeuner, dîner, terrasse, privatisation
- Sections : salles/ambiances, menus, calendrier créneaux (déjeuner/dîner)
- Formulaire : date, heure, nombre de couverts, nom, téléphone
- CTA : « Réserver une table »
- Pexels alt : « fine dining restaurant interior », « restaurant table setting », « french bistro terrace », « chef plated dish »""",
    ),
    SectorGeneratorProfile(
        id="spa-bien-etre-resa",
        kind="reservation",
        matcher_groups=(("spa", "bien-etre"), ("spa", "soin")),
        instructions="""SECTEUR : Spa & Bien-être (réservation)
- Vocabulaire : massage, soin, hammam, forfait duo, détente, praticien
- Sections : soins, forfaits, praticiens, calendrier créneaux
- Formulaire : soin choisi, date, créneau horaire, coordonnées
- CTA : « Réserver un soin »
- Pexels alt : « spa massage room », « wellness spa interior », « facial treatment spa », « relaxation spa candles »""",
    ),
    SectorGeneratorProfile(
        id="activites-loisirs",
        kind="reservation",
        matcher_groups=(("activites", "loisirs"),),
        instructions="""SECTEUR : Activités & Loisirs (réservation)
- Vocabulaire : session, pack famille, anniversaire, team building, carte cadeau, encadrant
- Sections : activités proposées, groupes, calendrier sessions, tarifs
- Formulaire inscription : activité, date/session, participants, contact
- CTA : « Réserver une session » / « S'inscrire »
- Pexels alt : « outdoor adventure activity », « family kayaking », « indoor climbing gym », « kids birthday party activity »""",
    ),
    SectorGeneratorProfile(
        id="location-nautique",
        kind="reservation",
        matcher_groups=(("nautique", "location"), ("location nautique",)),
        instructions="""SECTEUR : Location nautique (réservation)
- Vocabulaire : bateau, voilier, jet-ski, permis côtier, sortie guidée, marina
- Sections : flotte (bateaux/jet-skis), disponibilités, tarifs, permis requis
- Formulaire : embarcation, dates, durée, permis possédé
- CTA : « Réserver un bateau »
- Pexels alt : « motorboat marina », « sailing boat sea », « jet ski water », « yacht rental harbor »""",
    ),
    # —— E-commerce (6) ——
    SectorGeneratorProfile(
        id="mode-vetements",
        kind="ecommerce",
        matcher_groups=(("mode", "vetements"),),
        instructions="""SECTEUR : Mode & Vêtements (e-commerce)
- Catalogue produits (6+ articles) : nom, prix €, taille, couleur
- Filtres visuels taille/couleur (boutons ou select)
- Panier JS local (ajout, quantité, total)
- Formulaire commande : nom, email, adresse livraison
- CTA : « Ajouter au panier » / « Commander »
- Pexels alt : « fashion clothing store », « women dress boutique », « menswear collection », « shoes fashion product »""",
    ),
    SectorGeneratorProfile(
        id="artisan-createur",
        kind="ecommerce",
        matcher_groups=(("artisan", "createur"),),
        instructions="""SECTEUR : Artisan & Créateur (e-commerce)
- Galerie produits uniques faits main (story de l'artisan)
- Section « L'artisan » avec portrait et savoir-faire
- Panier + commande personnalisée (champ message option)
- CTA : « Commander » / « Demande sur mesure »
- Pexels alt : « handmade pottery workshop », « artisan craftsman studio », « handmade jewelry », « craft market products »""",
    ),
    SectorGeneratorProfile(
        id="bio-alimentation",
        kind="ecommerce",
        matcher_groups=(("bio", "alimentation"),),
        instructions="""SECTEUR : Bio & Alimentation (e-commerce)
- Catalogue produits frais / épicerie bio avec origine et prix
- Panier + livraison locale (zone, créneau)
- Option abonnement panier hebdomadaire
- CTA : « Ajouter au panier » / « Commander »
- Pexels alt : « organic vegetables market », « fresh farm produce », « organic grocery basket », « local farmers market »""",
    ),
    SectorGeneratorProfile(
        id="hightech-electronique",
        kind="ecommerce",
        matcher_groups=(("high-tech", "electronique"), ("high tech",), ("electronique",)),
        instructions="""SECTEUR : High-tech & Électronique (e-commerce)
- Fiches produit détaillées (specs, comparatif rapide)
- Panier + garantie 2 ans + SAV mentionné
- CTA : « Ajouter au panier » / « Acheter »
- Pexels alt : « smartphone product white background », « laptop computer modern », « wireless headphones », « gaming setup desk »""",
    ),
    SectorGeneratorProfile(
        id="maison-deco",
        kind="ecommerce",
        matcher_groups=(("maison", "deco"),),
        instructions="""SECTEUR : Maison & Déco (e-commerce)
- Catalogue par ambiances (salon, cuisine, chambre) avec zoom visuel
- Panier + délai livraison affiché par produit
- CTA : « Ajouter au panier »
- Pexels alt : « modern living room interior », « home decor furniture », « pendant lamp design », « cozy bedroom decor »""",
    ),
    SectorGeneratorProfile(
        id="fleurs-cadeaux",
        kind="ecommerce",
        matcher_groups=(("fleurs", "cadeaux"),),
        instructions="""SECTEUR : Fleurs & Cadeaux (e-commerce)
- Catalogue bouquets (occasion : mariage, anniversaire, deuil)
- Personnalisation message carte + livraison jour J
- Panier + formulaire livraison (date, adresse)
- CTA : « Commander » / « Offrir »
- Pexels alt : « flower bouquet roses », « gift box elegant », « florist shop flowers », « wedding flower arrangement »""",
    ),
    # —— Vitrine (9) ——
    SectorGeneratorProfile(
        id="artisan-btp",
        kind="vitrine",
        matcher_groups=(("artisan", "btp"),),
        instructions="""SECTEUR : Artisan & BTP (vitrine)
- Pages/sections dans l'ordre : Accueil → Services → Réalisations → Devis → Contact
- Vocabulaire : devis gratuit, chantier, dépannage, rénovation, savoir-faire local
- CTA principal : « Demander un devis » (secondaire : « Nous appeler »)
- Pexels alt : « construction worker renovation », « plumber repair home », « masonry craftsman », « electrician working »""",
    ),
    SectorGeneratorProfile(
        id="restaurant-cafe",
        kind="vitrine",
        matcher_groups=(("restauration",), ("restaurant", "cafe")),
        instructions="""SECTEUR : Restaurant & Café (vitrine)
- Pages/sections : Accueil → Menu → Galerie → Réservation → Contact
- Vocabulaire : carte du jour, produits locaux, chef, ambiance, terrasse
- CTA : « Réserver une table » / « Voir le menu »
- Pexels alt : « restaurant interior dining », « french cuisine plate », « coffee shop latte art », « restaurant terrace evening »""",
    ),
    SectorGeneratorProfile(
        id="sante-bien-etre",
        kind="vitrine",
        matcher_groups=(("sante", "bien-etre"), ("sante",),),
        instructions="""SECTEUR : Santé & Bien-être (vitrine)
- Pages/sections : Accueil → Praticien → Soins → Tarifs → RDV
- Vocabulaire : consultation, bilan, accompagnement, cabinet, téléconsultation
- CTA : « Prendre RDV »
- Pexels alt : « medical clinic reception », « therapist consultation », « wellness healthcare », « doctor patient consultation »""",
    ),
    SectorGeneratorProfile(
        id="nautique-marine",
        kind="vitrine",
        matcher_groups=(("nautique", "marine"),),
        instructions="""SECTEUR : Nautique & Marine (vitrine)
- Pages/sections : Accueil → Services → Flotte/équipe → Tarifs → Contact
- Vocabulaire : marina, entretien bateau, location, sortie en mer, hivernage
- CTA : « Demander un devis » / « Réserver une sortie »
- Pexels alt : « sailing boat harbor », « marina boats sunset », « yacht maintenance », « nautical team water »""",
    ),
    SectorGeneratorProfile(
        id="immobilier-architecture",
        kind="vitrine",
        matcher_groups=(("immobilier",), ("architecture",)),
        instructions="""SECTEUR : Immobilier & Architecture (vitrine)
- Pages/sections : Accueil → Biens → À propos → Estimation → Contact
- Vocabulaire : vente, location, estimation, visite virtuelle, prestige
- CTA : « Estimer mon bien » / « Nous contacter »
- Pexels alt : « luxury apartment interior », « modern house architecture », « real estate agent », « property facade modern »""",
    ),
    SectorGeneratorProfile(
        id="beaute-coiffure",
        kind="vitrine",
        matcher_groups=(("beaute", "coiffure"), ("coiffure",),),
        instructions="""SECTEUR : Beauté & Coiffure (vitrine)
- Pages/sections : Accueil → Prestations → Galerie → Tarifs → RDV
- Vocabulaire : coupe, coloration, soin, barbe, avant/après
- CTA : « Prendre RDV »
- Pexels alt : « hair salon interior », « hairdresser styling », « beauty treatment spa », « makeup artist studio »""",
    ),
    SectorGeneratorProfile(
        id="formation-coaching",
        kind="vitrine",
        matcher_groups=(("formation", "coaching"),),
        instructions="""SECTEUR : Formation & Coaching (vitrine)
- Pages/sections : Accueil → Formations → Formateur → Témoignages → Contact
- Vocabulaire : certification, module, coaching individuel, atelier, e-learning
- CTA : « Demander un devis » / « S'inscrire »
- Pexels alt : « professional training classroom », « business coach meeting », « workshop team learning », « online course laptop »""",
    ),
    SectorGeneratorProfile(
        id="garage-auto",
        kind="vitrine",
        matcher_groups=(("garage", "auto"), ("garage", "automobile"), ("garage",),),
        instructions="""SECTEUR : Garage & Auto (vitrine)
- Pages/sections : Accueil → Services → Tarifs → Équipe → Contact
- Vocabulaire : révision, pneus, diagnostic, carrosserie, contrôle technique
- CTA : « Demander un devis » / « Prendre RDV »
- Pexels alt : « auto repair garage », « car mechanic workshop », « tire service car », « car diagnostic technician »""",
    ),
    SectorGeneratorProfile(
        id="tourisme-loisirs",
        kind="vitrine",
        matcher_groups=(("tourisme", "loisirs"),),
        instructions="""SECTEUR : Tourisme & Loisirs (vitrine)
- Pages/sections : Accueil → Hébergements → Activités → Tarifs → Contact
- Vocabulaire : camping, gîte, hôtel, séjour, activités, nature, escapade
- CTA : « Réserver » / « Nous contacter »
- Pexels alt : « holiday cottage countryside », « hotel resort pool », « tourist activities hiking », « camping family vacation »""",
    ),
    # —— App web (5) ——
    SectorGeneratorProfile(
        id="dashboard-analytics",
        kind="app_web",
        matcher_groups=(("dashboard", "analytics"), ("dashboard",)),
        instructions="""SECTEUR : Dashboard & Analytics (app web)
- Vue 1 (Dashboard) : 4 KPI cards (chiffre + variation % + icône SVG) + graphique barres SVG inline (12 mois fictifs)
- Vue 2 : tableau transactions/événements (5-8 lignes fictives)
- Vue 3 : formulaire configuration des alertes (seuils, email, fréquence)
- Sidebar : Dashboard, Transactions, Alertes, Paramètres""",
    ),
    SectorGeneratorProfile(
        id="crm-clients",
        kind="crm",
        matcher_groups=(("crm", "clients"),),
        instructions="""SECTEUR : CRM Clients (générique)
- Terminologie : Clients, Contacts, Deals
- Pipeline Kanban 5 colonnes : Lead → Qualif → Démo → Proposition → Closing
- KPI Dashboard : contacts total, deals actifs, CA du mois, taux conversion
- Données fictives B2B françaises (PME, SaaS, conseil)""",
    ),
    SectorGeneratorProfile(
        id="crm-immobilier",
        kind="crm",
        matcher_groups=(("crm", "immobilier"),),
        instructions="""SECTEUR : CRM Immobilier
- Terminologie : Acquéreurs, Biens, Mandats (pas Clients/Deals génériques)
- Pipeline Kanban 5 colonnes : Contact → Visite → Offre → Compromis → Acte
- Contacts : acquéreurs et vendeurs, biens (appartement, maison) avec prix €
- Montants élevés (150k–800k €), villes françaises, dates clôture 2026""",
    ),
    SectorGeneratorProfile(
        id="crm-recrutement",
        kind="crm",
        matcher_groups=(("crm", "recrutement"),),
        instructions="""SECTEUR : CRM Recrutement
- Terminologie : Candidats, Postes, Process (pas Deals)
- Pipeline Kanban 5 colonnes : Sourcing → Screening → Entretien → Offre → Intégration
- Contacts : candidats avec poste visé, entreprises clientes, salaires €/an
- Activités : entretiens RH, relances, notes de screening""",
    ),
    SectorGeneratorProfile(
        id="crm-agence",
        kind="crm",
        matcher_groups=(("crm", "agence"),),
        instructions="""SECTEUR : CRM Agence
- Terminologie : Clients, Projets, Devis (pipeline = étapes projet)
- Pipeline Kanban 5 colonnes : Brief → Devis → Validation → Production → Livraison
- Deals = projets créatifs (refonte site, branding) avec montants devis €
- Contacts : directeurs marketing, startups, PME""",
    ),
    SectorGeneratorProfile(
        id="crm-coach",
        kind="crm",
        matcher_groups=(("crm", "coach"),),
        instructions="""SECTEUR : CRM Coach / Consultant
- Terminologie : Coachés, Sessions, Parcours (pas Clients/Deals)
- Pipeline Kanban 5 colonnes : Découverte → Bilan → Programme → Suivi → Résultats
- Contacts : coachés individuels ou dirigeants, forfaits coaching €
- Activités : sessions, bilans, objectifs SMART""",
    ),
    SectorGeneratorProfile(
        id="planning-rdv",
        kind="app_web",
        matcher_groups=(("planning", "rendez-vous"), ("planning", "rdv"), ("planning",)),
        instructions="""SECTEUR : Planning & RDV (app web)
- Vue 1 (Dashboard) : grille calendrier semaine (7 colonnes × créneaux horaires) avec RDV colorés par statut
- Vue 2 : liste RDV du jour avec actions Confirmer / Annuler (5-8 entrées)
- Vue 3 : formulaire nouveau RDV (client, date, heure, durée, notes)
- Sidebar : Calendrier, RDV du jour, Nouveau RDV, Paramètres""",
    ),
    SectorGeneratorProfile(
        id="gestion-entreprise",
        kind="app_web",
        matcher_groups=(("gestion", "entreprise"), ("gestion",)),
        instructions="""SECTEUR : Gestion d'entreprise (app web)
- Vue 1 (Dashboard) : Kanban 3 colonnes (À faire / En cours / Terminé) avec cards projets
- Vue 2 : liste projets avec membres et deadlines (5-8 lignes)
- Vue 3 : formulaire nouveau projet (titre, client, deadline, membres, statut)
- Sidebar : Kanban, Projets, Nouveau projet, Paramètres""",
    ),
    SectorGeneratorProfile(
        id="stock-inventaire",
        kind="app_web",
        matcher_groups=(("stock", "inventaire"), ("stock",), ("inventaire",)),
        instructions="""SECTEUR : Stock & Inventaire (app web)
- Vue 1 (Dashboard) : grille produits avec badge stock (Disponible / Faible / Rupture) sur chaque card
- Vue 2 : tableau mouvements entrées/sorties avec dates (5-8 lignes)
- Vue 3 : formulaire ajout produit (nom, SKU, quantité, seuil alerte, emplacement)
- Sidebar : Inventaire, Mouvements, Ajouter produit, Paramètres
- OBLIGATOIRE : badges « Disponible », « Faible » ou « Rupture » visibles sur les produits""",
    ),
)

_DEFAULT_BY_KIND: dict[SectorKind, str] = {
    "vitrine": """SECTEUR : Vitrine générique
- Sections : Accueil, Services, Galerie, À propos, Contact
- CTA : « Nous contacter » / « Demander un devis »
- Pexels alt : termes professionnels liés au brief (secteur + services)""",
    "reservation": """SECTEUR : Réservation générique
- Appliquer structure site_reservation (slider, hébergements, calendrier, formulaire)
- CTA : « Réserver »
- Pexels alt : hébergement + activité selon description du brief""",
    "ecommerce": """SECTEUR : E-commerce générique
- Catalogue produits, panier JS, formulaire commande
- CTA : « Ajouter au panier » / « Commander »
- Pexels alt : produits nommés selon le secteur du brief""",
    "app_web": """SECTEUR : Application web générique
- Vues sidebar : Login, Dashboard, Vue principale, Détail, Paramètres
- Données fictives cohérentes avec database_schema du brief
- Formulaires alignés sur les colonnes des tables
- Rôles auth_schema affichés dans Paramètres ou header""",
    "crm": """SECTEUR : CRM générique
- Terminologie : Contacts, Deals, Pipeline, Activités
- Pipeline Kanban 5 colonnes avec étapes métier du secteur brief
- 5 vues : Dashboard, Contacts, Pipeline, Activités, Fiche contact
- Données fictives françaises, montants €, dates 2026""",
}


def resolve_sector_generator_profile(
    brief: dict[str, Any],
) -> SectorGeneratorProfile | None:
    kind = _brief_kind(brief)
    sector_norm = _normalize_sector_text(_extract_sector_from_brief(brief))
    if not sector_norm:
        return None
    for profile in SECTOR_GENERATOR_PROFILES:
        if profile.kind != kind:
            continue
        if _profile_matches(sector_norm, profile):
            return profile
    return None


def build_sector_generator_appendix(brief: dict[str, Any]) -> str:
    """Bloc à injecter dans le prompt système GeneratorAI selon secteur + type projet."""
    kind = _brief_kind(brief)
    profile = resolve_sector_generator_profile(brief)
    sector_raw = _extract_sector_from_brief(brief)

    lines = [
        "### ADAPTATION SECTEUR (obligatoire)",
        f"Type projet détecté : {kind}.",
    ]
    if sector_raw:
        lines.append(f"Secteur brief : « {sector_raw} ».")
    if profile:
        lines.append(profile.instructions)
    else:
        lines.append(_DEFAULT_BY_KIND[kind or "vitrine"])
    if kind == "crm":
        lines.append(
            "Règles communes CRM : vocabulaire métier français du secteur, 5 vues minimum "
            "avec switcher JS, pipeline Kanban visuel (cursor:grab), données fictives "
            "réalistes (noms FR, €, dates 2026), champs alignés sur database_schema, "
            "rôles auth_schema visibles dans Paramètres."
        )
        return CRM_APPENDIX + "\n\n" + "\n".join(lines)
    if kind == "app_web":
        lines.append(
            "Règles communes app web : vocabulaire métier français, 3 vues minimum "
            "avec switcher JS, données fictives réalistes, champs formulaires alignés "
            "sur database_schema, rôles auth_schema visibles dans l'UI."
        )
    else:
        lines.append(
            "Règles communes : vocabulaire métier français, sections dans l'ordre indiqué, "
            "CTA cohérents, chaque <img class='pexels-inject'> avec un alt descriptif "
            "en anglais (3-6 mots) reprenant les requêtes Pexels du secteur."
        )
    return "\n".join(lines)


def is_app_web_brief(brief: dict[str, Any]) -> bool:
    return _brief_kind(brief) == "app_web"


def is_crm_brief(brief: dict[str, Any]) -> bool:
    return _brief_kind(brief) == "crm"


APP_WEB_APPENDIX = """
MODE APPLICATION WEB (project_type application_web ou real_app) :
Page 100 % autonome — HTML + CSS + JavaScript inline. ZÉRO fetch/API externe.
PAS de hero vitrine, PAS de Pexels, PAS de Playfair Display — Inter uniquement.

IDS OBLIGATOIRES (exactement ces attributs id) :
- id="login-screen" : visible par défaut (display:flex ou block)
- id="app-shell" : caché par défaut (display:none)
- id="login-password" sur le champ mot de passe
- Chaque vue : id="view-dashboard", id="view-list", id="view-form" (ou noms métier cohérents)
- Sidebar nav items avec data-view="view-dashboard" etc.

STRUCTURE OBLIGATOIRE :

1) ÉCRAN LOGIN (#login-screen, affiché par défaut)
   - Pleine page centrée, fond #0f1117
   - Logo client + nom de l'app (client_name du brief)
   - Formulaire : email + mot de passe
   - Bouton « Se connecter » couleur_primaire du brief
   - JS onclick sur le bouton :
     * si mot de passe === "demo2024" → cache #login-screen, affiche #app-shell
     * sinon alert("Mot de passe incorrect")
   - Mention discrète : « Démo : demo2024 »

2) APP SHELL (#app-shell, display:none par défaut)
   - Layout flex horizontal, min-height 100vh, fond #0f1117

   SIDEBAR (fixe gauche, 240px, fond #161b27) :
   - Logo + nom client en haut
   - Minimum 3 items navigation avec icônes SVG inline (stroke, 20px)
   - Item actif : couleur couleur_primaire, fond couleur_primaire à 10% opacity
   - Bouton « Déconnexion » en bas → cache #app-shell, affiche #login-screen
   - Sous 768px : sidebar en hamburger (bouton ☰, sidebar slide-in)

   ZONE CONTENU (flex:1, overflow-y:auto, padding 24px) :
   - Header : titre vue active + bouton « + Nouveau » (couleur_primaire)
   - Une seule vue visible à la fois (les autres display:none)
   - Footer minimal dans app-shell (copyright client)

VUES OBLIGATOIRES (minimum 3, switcher JS via sidebar) :
   - Vue 1 : vue principale du secteur (voir instructions secteur)
   - Vue 2 : liste/tableau 5-8 entrées fictives cohérentes
   - Vue 3 : formulaire création/édition

JAVASCRIPT OBLIGATOIRE (scope global, avant </body>) :
function showView(viewId) {
  document.querySelectorAll('[id^="view-"]').forEach(v => v.style.display = 'none');
  const el = document.getElementById(viewId);
  if (el) el.style.display = 'block';
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const nav = document.querySelector('[data-view="' + viewId + '"]');
  if (nav) nav.classList.add('active');
  const title = document.getElementById('view-title');
  if (title && nav) title.textContent = nav.textContent.trim();
}
function login() {
  const pwd = document.getElementById('login-password').value;
  if (pwd === 'demo2024') {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-shell').style.display = 'flex';
    showView('view-dashboard');
  } else { alert('Mot de passe incorrect'); }
}
function logout() {
  document.getElementById('app-shell').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
}
// Hamburger mobile : toggle .sidebar-open sur body ou sidebar

INJECTION AUTH & DATABASE (OBLIGATOIRE) :
- Lire ## database_schema et ## auth_schema du message utilisateur
- Noms de tables → titres des vues/sections (ex: table "contacts" → vue Clients)
- Colonnes des tables → champs dans formulaires et colonnes tableaux
- auth_type et roles → afficher dans vue Paramètres ou badge header (ex: « Accès : admin »)
- Si auth_schema absent → interface single_user par défaut
- Si database_schema absent → données fictives génériques (users, items)

DESIGN OBLIGATOIRE :
- Fond global : #0f1117
- Sidebar : #161b27
- Cards/panels : #1e2535, border 1px solid rgba(255,255,255,0.08), border-radius 12px
- couleur_primaire du brief : accents, boutons, item nav actif, KPI highlights
- Google Fonts : Inter uniquement (<link> dans <head>)
- Texte principal : #e2e8f0
- Texte secondaire : #8892a4
- Graphiques : SVG inline uniquement (pas Chart.js, pas CDN)
- Tableaux : header #161b27, lignes alternées rgba(255,255,255,0.03)
- Inputs : fond #161b27, border rgba(255,255,255,0.12), focus couleur_primaire
- Responsive : sidebar collapse hamburger < 768px

INTERDIT :
- fetch(), XMLHttpRequest, appels API externes
- Librairies JS/CSS externes (sauf Google Fonts Inter)
- Hero vitrine plein écran, images Pexels
- Placeholder visible dans le contenu

Document COMPLET : <html><head><style>...</style></head><body>...</body></html>
Minimum 4000 caractères. CSS compact (réutiliser classes .card, .btn, .table).
Priorité absolue : document COMPLET terminé par </footer></body></html>.
Si limite de place : réduire les données fictives, jamais couper la fin du document.
"""


CRM_APPENDIX = """
MODE CRM (project_type crm ou TYPE: crm) :
Page 100 % autonome — HTML + CSS + JavaScript inline. ZÉRO fetch/API externe.
PAS de hero vitrine, PAS de Pexels — Inter uniquement.

IDS OBLIGATOIRES (exactement ces attributs id) :
- id="login-screen" : visible par défaut (display:flex ou block)
- id="app-shell" : caché par défaut (display:none)
- id="login-password" sur le champ mot de passe
- id="view-dashboard", id="view-contacts", id="view-pipeline", id="view-activities",
  id="view-contact-detail" (fiche contact — modal ou vue pleine page)
- id="view-settings" pour Paramètres
- Sidebar nav items avec data-view="view-dashboard" etc.

STRUCTURE OBLIGATOIRE :

1) ÉCRAN LOGIN (#login-screen, affiché par défaut)
   - Pleine page centrée, fond #0f1117
   - Logo client + nom de l'app (client_name du brief)
   - Formulaire : email + mot de passe
   - Bouton « Se connecter » couleur_primaire du brief
   - JS onclick : mot de passe === "demo2024" → cache #login-screen, affiche #app-shell
   - sinon alert("Mot de passe incorrect")
   - Mention discrète : « Démo : demo2024 »

2) APP SHELL (#app-shell, display:none par défaut)
   - Layout flex horizontal, min-height 100vh, fond #0f1117

   SIDEBAR (fixe gauche, 240px, fond #161b27) :
   - Logo + nom client en haut
   - Items navigation CRM avec icônes SVG inline (stroke, 20px) :
     Dashboard, Contacts, Pipeline, Activités, Paramètres
   - Item actif : couleur couleur_primaire, fond couleur_primaire à 10% opacity
   - Bouton « Déconnexion » en bas → logout()
   - Sous 768px : hamburger (☰, sidebar slide-in)

   HEADER (zone contenu) :
   - Titre vue active (id="view-title")
   - Bouton « + Nouveau contact » couleur_primaire

   ZONE CONTENU (flex:1, overflow-y:auto, padding 24px) :
   - Une seule vue visible à la fois (les autres display:none)

VUES OBLIGATOIRES (5 minimum) :

Vue 1 — Dashboard (#view-dashboard) :
   - 4 KPI cards : Contacts total / Deals actifs / CA du mois / Taux conversion
   - Graphique pipeline : barres SVG inline par stage (5 étapes du secteur)
   - Liste des 5 dernières activités

Vue 2 — Contacts (#view-contacts) :
   - Grille cards contacts (8 contacts fictifs)
   - Chaque card : avatar initiales, nom, entreprise, email, téléphone,
     badge statut (Prospect / Client / Inactif)
   - Filtres pills : Tous / Prospects / Clients / Inactifs
   - Champ recherche + bouton recherche
   - Clic card → showView('view-contact-detail') ou ouvrir modal fiche

Vue 3 — Pipeline Kanban (#view-pipeline) — VUE CLÉ :
   - 5 colonnes selon secteur (voir instructions secteur)
   - Chaque colonne : header avec nombre de deals + montant total €
   - Cards deals : nom contact, montant €, date clôture estimée (2026), probabilité %
   - Cards style draggable : cursor:grab (pas de JS drag réel)
   - Colonne finale « Gagné » (ou équivalent secteur) : border-top couleur_primaire

Vue 4 — Activités (#view-activities) :
   - Timeline verticale
   - Types : Appel / Email / RDV / Note avec icônes SVG inline
   - Chaque activité : contact lié, date, description, statut

Vue 5 — Fiche Contact (#view-contact-detail) :
   - Nom complet, entreprise, coordonnées
   - Score lead : jauge SVG 0-100
   - Mini timeline interactions
   - Deals associés (liste ou cards)
   - Boutons : Appeler / Envoyer email / Créer deal

RÈGLES PAR SECTEUR (brief.sector) :
- CRM / clients : Clients, Contacts, Deals — Lead → Qualif → Démo → Proposition → Closing
- CRM / immobilier : Acquéreurs, Biens, Mandats — Contact → Visite → Offre → Compromis → Acte
- CRM / recrutement : Candidats, Postes, Process — Sourcing → Screening → Entretien → Offre → Intégration
- CRM / agence : Clients, Projets, Devis — Brief → Devis → Validation → Production → Livraison
- CRM / coach : Coachés, Sessions, Parcours — Découverte → Bilan → Programme → Suivi → Résultats

JAVASCRIPT OBLIGATOIRE (scope global, avant </body>) :
function showView(viewId) {
  document.querySelectorAll('[id^="view-"]').forEach(v => v.style.display = 'none');
  const el = document.getElementById(viewId);
  if (el) el.style.display = 'block';
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const nav = document.querySelector('[data-view="' + viewId + '"]');
  if (nav) nav.classList.add('active');
  const title = document.getElementById('view-title');
  if (title && nav) title.textContent = nav.textContent.trim();
}
function login() { /* même logique demo2024 que app web */ }
function logout() { /* cache app-shell, affiche login-screen */ }
function filterContacts(status) { /* filtre pills contacts */ }

INJECTION AUTH & DATABASE (OBLIGATOIRE) :
- Lire ## database_schema et ## auth_schema du message utilisateur
- Noms de tables → sections CRM (ex: table "contacts" → vue Contacts)
- Colonnes → champs cards/formulaires
- auth_type et roles → vue Paramètres ou badge header
- Si schemas absents → données fictives CRM génériques

DESIGN CRM OBLIGATOIRE :
- Fond global : #0f1117
- Sidebar : #161b27
- Cards contacts : #1e2535, border 1px solid rgba(255,255,255,0.08), border-radius 12px
- Colonnes pipeline : #161b27, border-top 3px couleur_primaire sur colonne gagnée/active
- Badges : vert=Gagné/Client, amber=En cours/Prospect actif, rouge=Perdu/Inactif
- couleur_primaire : accents, boutons, KPI, colonne gagnée
- Google Fonts : Inter uniquement
- Texte principal #e2e8f0, secondaire #8892a4
- Graphiques et jauges : SVG inline uniquement
- Responsive : sidebar hamburger < 768px

INTERDIT :
- fetch(), XMLHttpRequest, API externes
- Librairies JS/CSS externes (sauf Google Fonts Inter)
- Hero vitrine, images Pexels
- Placeholder visible

Document COMPLET : <html><head><style>...</style></head><body>...</body></html>
Minimum 5000 caractères. CSS compact (classes .card, .btn, .badge, .kanban-col).
Priorité absolue : document COMPLET terminé par </footer></body></html>.
Si limite de place : réduire données fictives, jamais couper la fin.
"""


ECOMMERCE_APPENDIX = """
MODE E-COMMERCE (project_type ou TYPE: ecommerce) :
Page 100 % autonome — HTML + CSS + JavaScript inline. ZÉRO fetch/API externe.

Structure obligatoire :
1) Navbar + hero (nom boutique, accroche secteur)
2) Section catalogue (#catalogue) : grille produits (min. 6 cards)
   - Chaque produit : <img class="pexels-inject">, nom, prix €, bouton « Ajouter au panier »
   - data-product-id, data-product-name, data-price sur chaque card
3) Section panier (#panier) : liste articles, quantités, sous-total, total
4) Section commande (#commande) : formulaire nom, email, téléphone, adresse, bouton « Commander »
5) Message succès local après commande (pas d'envoi réseau)
6) Footer

JavaScript obligatoire (<script> avant </body>) :
- État panier : window.cart = [] (tableau global {id, name, price, qty, size})
- addToCart(id, name, price, size) : ajoute ou incrémente qty, appelle renderCart()
- removeFromCart(id) : retire du tableau, appelle renderCart()
- updateQty(id, delta) : modifie qty, retire si qty <= 0, appelle renderCart()
- renderCart() : vide #cart-items, recrée les lignes, met à jour #cart-total et badge navbar
- submitOrder() : valide champs formulaire, affiche #order-success, vide panier
- Chaque bouton "Ajouter au panier" : onclick="addToCart('PRODUCT_ID', 'NOM', PRIX, 'TAILLE_DEFAULT')"
- Badge panier navbar : <span id="cart-count">0</span> mis à jour à chaque renderCart()
- DOMContentLoaded : initialiser renderCart()
IMPORTANT : ne jamais laisser les boutons sans onclick. Tester mentalement que addToCart fonctionne.

RÈGLES ABSOLUES JAVASCRIPT E-COMMERCE (TOUS TYPES) :

RÈGLE 0 — SCOPE GLOBAL OBLIGATOIRE :
Toutes les fonctions interactives DOIVENT être dans le scope global.
Structure OBLIGATOIRE du <script> (avant </body>) :

<script>
// ═══ ÉTAT GLOBAL ═══
window.cart = [];

// ═══ FONCTIONS GLOBALES (onclick accessibles) ═══
function addToCart(btn) {
  const card = btn.closest('[data-id]') || btn.closest('.product-card');
  const id = card.dataset.id || card.dataset.productId;
  const name = card.dataset.name || card.dataset.productName;
  const price = parseFloat(card.dataset.price || card.dataset.productPrice);
  const sizeEl = card.querySelector('select');
  const size = sizeEl ? sizeEl.value : '';
  const existing = window.cart.find(i => i.id === id && i.size === size);
  if (existing) { existing.qty++; } else { window.cart.push({id, name, price, qty:1, size}); }
  renderCart();
}

function removeFromCart(id) {
  window.cart = window.cart.filter(i => i.id !== id);
  renderCart();
}

function updateQty(id, delta) {
  const item = window.cart.find(i => i.id === id);
  if (item) { item.qty += delta; if (item.qty <= 0) removeFromCart(id); else renderCart(); }
}

function renderCart() {
  const items = document.getElementById('cart-items');
  const total = document.getElementById('cart-total');
  const count = document.getElementById('cart-count');
  if (count) count.textContent = window.cart.reduce((s,i) => s+i.qty, 0);
  if (!items) return;
  if (window.cart.length === 0) { items.innerHTML = '<p style="color:#999;text-align:center;padding:20px">Votre panier est vide</p>'; }
  else { items.innerHTML = window.cart.map(i => `<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee"><span>${i.name} ${i.size ? '('+i.size+')' : ''}</span><span><button onclick="updateQty('${i.id}',-1)" style="margin:0 5px;cursor:pointer">−</button>${i.qty}<button onclick="updateQty('${i.id}',1)" style="margin:0 5px;cursor:pointer">+</button> ${(i.price*i.qty).toFixed(2)}€ <button onclick="removeFromCart('${i.id}')" style="color:red;margin-left:10px;cursor:pointer">✕</button></span></div>`).join(''); }
  const t = window.cart.reduce((s,i) => s+i.price*i.qty, 0);
  if (total) total.textContent = t.toFixed(2) + ' €';
}

function filterProducts(cat) {
  document.querySelectorAll('.product-card, [data-category]').forEach(card => {
    const c = card.dataset.category || '';
    card.style.display = (cat === 'tous' || cat === 'all' || c.toLowerCase().includes(cat.toLowerCase())) ? '' : 'none';
  });
  document.querySelectorAll('.filter-btn, [onclick*="filterProducts"]').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.toLowerCase().includes(cat.toLowerCase()) || (cat === 'tous' && btn.textContent.toLowerCase().includes('tous')));
  });
}

function submitOrder() {
  const form = document.getElementById('order-form') || document.querySelector('form');
  if (form) {
    const required = form.querySelectorAll('[required]');
    for (const field of required) {
      if (!field.value.trim()) { field.focus(); alert('Veuillez remplir tous les champs obligatoires.'); return; }
    }
  }
  if (window.cart.length === 0) { alert('Votre panier est vide.'); return; }
  window.cart = [];
  renderCart();
  const success = document.getElementById('order-success');
  if (success) { success.style.display = 'block'; success.scrollIntoView({behavior:'smooth'}); }
  else { alert('Commande confirmée ! Merci pour votre achat.'); }
}

// ═══ INIT ═══
document.addEventListener('DOMContentLoaded', function() {
  renderCart();
});
</script>

INTERDIT : déclarer addToCart, filterProducts, renderCart, submitOrder,
removeFromCart, updateQty à l'intérieur de DOMContentLoaded.
INTERDIT : utiliser scrollIntoView sans vérifier que l'élément existe.

Design premium obligatoire :
- Hero : min-height 100vh, background image Pexels (class="pexels-inject" alt="fashion boutique store") avec overlay couleur_primaire/80, titre blanc centré, CTA blanc border-radius 50px
- Catalogue : fond blanc cassé #fafafa, cards avec box-shadow 0 4px 20px rgba(0,0,0,0.08), border-radius 16px, hover transform translateY(-4px) transition 0.3s
- Prix : couleur_primaire, font-weight 700
- Boutons "Ajouter au panier" : bg couleur_primaire, border-radius 50px, width 100%, padding 12px
- Section panier : fond blanc, card récap glassmorphism border border-gray-100 rounded-2xl p-6
- Section commande : fond gris clair #f8f8f8, inputs border border-gray-200 rounded-lg focus:border couleur_primaire
- Google Fonts : Playfair Display (titres) + Inter (body)
- Navbar : fond blanc, box-shadow légère, sticky top-0
Maximum 15000 caractères.
"""
