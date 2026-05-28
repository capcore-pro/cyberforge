"""
Données fictives contextualisées selon le prompt et le type ArchitectAI.

Détecte un secteur (marketing, immobilier, restaurant, …) et fournit KPIs,
contacts CRM, factures, etc. adaptés au métier demandé.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tools.prompt_seed_hints import PromptSeedHints

# —— Détection secteur ——

_VERTICAL_MARKETING = (
    "marketing",
    "agence marketing",
    "agence digitale",
    "publicité",
    "publicite",
    "campagne",
    "campagnes",
    "lead",
    "leads",
    "roi",
    "ctr",
    "clics",
    "clic",
    "ads",
    "sea",
    "sem",
    "social ads",
    "acquisition",
    "conversion",
    "emailing",
    "newsletter",
    "brand awareness",
)
_VERTICAL_REAL_ESTATE = (
    "immobilier",
    "immobilière",
    "immobiliere",
    "mandat",
    "mandats",
    "appartement",
    "appartements",
    "maison",
    "maisons",
    "bien",
    "biens",
    "visite",
    "visites",
    "agent immobilier",
    "agence immobilière",
    "agence immobiliere",
    "location",
    "vente",
    "louer",
    "acheteur",
    "vendeur",
    "estimation",
    "diagnostic",
)
_VERTICAL_RESTAURANT = (
    "restaurant",
    "restaurants",
    "café",
    "cafe",
    "boulangerie",
    "brasserie",
    "menu",
    "carte",
    "carte des",
    "plat",
    "plats",
    "chef",
    "cuisine",
    "gastronomie",
    "gastronomique",
    "bistrot",
    "pizzeria",
    "sushi",
    "traiteur",
    "food",
    "réservation table",
    "reservation table",
    "couvert",
    "couverts",
    "service en salle",
    "sommelier",
)
_VERTICAL_HEALTH = (
    "santé",
    "sante",
    "clinique",
    "médecin",
    "medecin",
    "patient",
    "patients",
    "cabinet",
    "pharma",
    "hopital",
    "hôpital",
)
_VERTICAL_ARTISAN = (
    "artisan",
    "plombier",
    "plomberie",
    "électricien",
    "electricien",
    "électricité",
    "electricite",
    "chauffagiste",
    "serrurier",
    "peintre",
    "rénovation",
    "renovation",
    "dépannage",
    "depannage",
)
_VERTICAL_BEAUTY = (
    "coiffure",
    "coiffeur",
    "salon",
    "barbier",
    "esthétique",
    "esthetique",
    "ongles",
    "manucure",
    "spa",
    "institut",
)
_VERTICAL_FITNESS = (
    "fitness",
    "gym",
    "salle de sport",
    "coach",
    "coaching",
    "crossfit",
    "yoga",
    "pilates",
    "musculation",
)
_VERTICAL_FINANCE = (
    "finance",
    "fintech",
    "banque",
    "assurance",
    "crédit",
    "credit",
    "investissement",
    "portefeuille",
    "trading",
)


def detect_demo_vertical(prompt: str, *, project_type_label: str = "") -> str:
    """Retourne marketing | real_estate | restaurant | health | finance | artisan | beauty | fitness | generic."""
    blob = f"{project_type_label}\n{prompt}".lower()

    scores: dict[str, int] = {
        "marketing": sum(1 for k in _VERTICAL_MARKETING if k in blob),
        "real_estate": sum(1 for k in _VERTICAL_REAL_ESTATE if k in blob),
        "restaurant": sum(1 for k in _VERTICAL_RESTAURANT if k in blob),
        "health": sum(1 for k in _VERTICAL_HEALTH if k in blob),
        "finance": sum(1 for k in _VERTICAL_FINANCE if k in blob),
        "artisan": sum(1 for k in _VERTICAL_ARTISAN if k in blob),
        "beauty": sum(1 for k in _VERTICAL_BEAUTY if k in blob),
        "fitness": sum(1 for k in _VERTICAL_FITNESS if k in blob),
    }
    if re.search(r"\bagence\s+marketing\b", blob):
        scores["marketing"] += 4
    if re.search(r"\bcrm\b", blob) and scores["real_estate"] > 0:
        scores["real_estate"] += 2
    if "dashboard" in blob and scores["marketing"] > 0:
        scores["marketing"] += 2
    if re.search(r"\b(restaurant|café|cafe|bistrot|gastronom)\b", blob):
        scores["restaurant"] += 3
    if re.search(r"\b(plombier|électricien|electricien|chauffagiste|serrurier|dépannage|depannage)\b", blob):
        scores["artisan"] += 3
    if re.search(r"\b(coiffure|barbier|esthétique|esthetique|institut)\b", blob):
        scores["beauty"] += 3
    if re.search(r"\b(fitness|gym|crossfit|yoga|pilates)\b", blob):
        scores["fitness"] += 3
    label_lower = project_type_label.lower()
    if "site web" in label_lower and scores["restaurant"] > 0:
        scores["restaurant"] += 1
    if ("tableau de bord" in label_lower or "saas" in label_lower) and scores["marketing"] > 0:
        scores["marketing"] += 2

    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return "generic"


def _hints_or_build(
    hints: PromptSeedHints | None,
    prompt: str,
    project_type_label: str,
) -> PromptSeedHints:
    if hints is not None:
        return hints
    from tools.prompt_seed_hints import build_prompt_seed_hints

    return build_prompt_seed_hints(prompt, project_type_label=project_type_label)


def _campaign_list(hints: PromptSeedHints) -> list[str]:
    if hints.campaign_names:
        return list(hints.campaign_names)
    return ["Performance SEA Q2", "Social Ads Luxe", "Lead Gen Automne", "Retargeting panier"]


def _with_brand(rows: list[dict[str, Any]], brand_name: str, company_key: str = "company") -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        item = {k: str(v) for k, v in row.items()}
        if i == 0 and brand_name:
            item[company_key] = brand_name
        out.append(item)
    return out


# —— CRM ——

def contextual_crm_contacts(
    *,
    vertical: str,
    brand_name: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str]]:
    h = _hints_or_build(hints, prompt, project_type_label)
    brand = brand_name or h.brand_name
    if vertical == "marketing":
        camps = _campaign_list(h)
        rows = [
            {
                "id": "1",
                "company": brand or "Pulse Agency",
                "person": "Camille Rousseau",
                "status": "Prospect",
                "email": "camille@pulse-agency.fr",
                "role_line": f"Camille Rousseau — Campagne « {camps[0]} »",
                "deal_value": "24 800 €",
            },
            {
                "id": "2",
                "company": "Luxe Retail Group",
                "person": "Marc Delaunay",
                "status": "Client",
                "email": "marc.delaunay@luxeretail.fr",
                "role_line": f"Marc Delaunay — Retainer {camps[1] if len(camps) > 1 else 'Social Ads'}",
                "deal_value": "41 200 €",
            },
            {
                "id": "3",
                "company": "GreenMobility",
                "person": "Inès Benali",
                "status": "Prospect",
                "email": "i.benali@greenmobility.io",
                "role_line": f"Inès Benali — Lead gen « {camps[2] if len(camps) > 2 else 'Automne'} »",
                "deal_value": "18 500 €",
            },
            {
                "id": "4",
                "company": "NovaFoods",
                "person": "Julien Perrin",
                "status": "Perdu",
                "email": "j.perrin@novafoods.fr",
                "role_line": f"Julien Perrin — Budget {camps[3] if len(camps) > 3 else 'display'} gelé",
                "deal_value": "—",
            },
        ]
    elif vertical == "restaurant":
        cuisine = h.cuisine_label or "cuisine bistronomique"
        rows = [
            {
                "id": "1",
                "company": brand,
                "person": "Élodie Marchand",
                "status": "Client",
                "email": "elodie@tables.fr",
                "role_line": f"Élodie Marchand — Réservation groupe 12 couverts",
                "deal_value": "680 €",
            },
            {
                "id": "2",
                "company": "Carte saison printemps",
                "person": "Chef Antoine Leroy",
                "status": "Prospect",
                "email": "chef@restaurant.fr",
                "role_line": f"Chef Leroy — Menu dégustation {cuisine}",
                "deal_value": "—",
            },
            {
                "id": "3",
                "company": "Partenaire terroir",
                "person": "Luc Moreau",
                "status": "Client",
                "email": "luc@producteurs.fr",
                "role_line": "Luc Moreau — Livraison produits frais (mardi)",
                "deal_value": "1 240 €",
            },
            {
                "id": "4",
                "company": "Critique Gault&Millau",
                "person": "Sophie Bernard",
                "status": "Prospect",
                "email": "s.bernard@gault.fr",
                "role_line": "Sophie Bernard — Dégustation presse jeudi",
                "deal_value": "—",
            },
        ]
    elif vertical == "real_estate":
        rows = [
            {
                "id": "1",
                "company": brand_name or "Habitat Plus",
                "person": "Sophie Lemaire",
                "status": "Prospect",
                "email": "s.lemaire@habitatplus.fr",
                "role_line": "Sophie Lemaire — Acheteuse T3 Lyon 6e",
                "deal_value": "285 000 €",
            },
            {
                "id": "2",
                "company": "Mandat T4 Villeurbanne",
                "person": "Philippe Garnier",
                "status": "Client",
                "email": "p.garnier@vendeur.fr",
                "role_line": "Philippe Garnier — Vendeur exclusif",
                "deal_value": "412 000 €",
            },
            {
                "id": "3",
                "company": "Studio investissement",
                "person": "Nadia El Amrani",
                "status": "Prospect",
                "email": "n.elamrani@invest.fr",
                "role_line": "Nadia El Amrani — Investisseuse locative",
                "deal_value": "156 000 €",
            },
            {
                "id": "4",
                "company": "Maison familiale Villefranche",
                "person": "Thomas Rey",
                "status": "Perdu",
                "email": "t.rey@acheteur.fr",
                "role_line": "Thomas Rey — Mandat expiré",
                "deal_value": "—",
            },
        ]
    elif vertical == "artisan":
        rows = [
            {
                "id": "1",
                "company": brand,
                "person": "Sophie Martin",
                "status": "Client",
                "email": "sophie.martin@gmail.com",
                "role_line": "Sophie Martin — Dépannage fuite cuisine (priorité)",
                "deal_value": "290 €",
            },
            {
                "id": "2",
                "company": "Rénovation salle de bain",
                "person": "Marc & Julie Leroy",
                "status": "Prospect",
                "email": "leroy.famille@gmail.com",
                "role_line": "Devis rénovation complète (douche italienne)",
                "deal_value": "6 800 €",
            },
            {
                "id": "3",
                "company": "Contrat entretien",
                "person": "Philippe Garnier",
                "status": "Client",
                "email": "p.garnier@proton.me",
                "role_line": "Entretien annuel chaudière + pièces",
                "deal_value": "180 €",
            },
            {
                "id": "4",
                "company": "Urgence week-end",
                "person": "Inès Benali",
                "status": "Prospect",
                "email": "ines.benali@gmail.com",
                "role_line": "Canalisation bouchée — intervention 24h",
                "deal_value": "—",
            },
        ]
    elif vertical == "beauty":
        rows = [
            {
                "id": "1",
                "company": brand,
                "person": "Camille Rousseau",
                "status": "Client",
                "email": "camille.rousseau@gmail.com",
                "role_line": "Balayage + coupe — fidélité (5e visite)",
                "deal_value": "145 €",
            },
            {
                "id": "2",
                "company": "Forfait mariée",
                "person": "Nadia El Amrani",
                "status": "Prospect",
                "email": "nadia.elamrani@gmail.com",
                "role_line": "Essai + chignon — date 14/06",
                "deal_value": "320 €",
            },
            {
                "id": "3",
                "company": "Barbe & entretien",
                "person": "Thomas Rey",
                "status": "Client",
                "email": "thomas.rey@gmail.com",
                "role_line": "Barbier — créneau mensuel",
                "deal_value": "35 €",
            },
            {
                "id": "4",
                "company": "Cartes cadeaux",
                "person": "Sophie Bernard",
                "status": "Prospect",
                "email": "sophie.bernard@gmail.com",
                "role_line": "Achat carte cadeau — 2 prestations",
                "deal_value": "—",
            },
        ]
    elif vertical == "fitness":
        rows = [
            {
                "id": "1",
                "company": brand,
                "person": "Julien Perrin",
                "status": "Prospect",
                "email": "julien.perrin@gmail.com",
                "role_line": "Essai 7 jours + onboarding coach",
                "deal_value": "—",
            },
            {
                "id": "2",
                "company": "Pack coaching",
                "person": "Inès Benali",
                "status": "Client",
                "email": "ines.benali@gmail.com",
                "role_line": "Pack 10 séances — objectif renfo",
                "deal_value": "490 €",
            },
            {
                "id": "3",
                "company": "Abonnement annuel",
                "person": "Sophie Lemaire",
                "status": "Client",
                "email": "sophie.lemaire@gmail.com",
                "role_line": "Renouvellement — prélèvement SEPA",
                "deal_value": "420 €",
            },
            {
                "id": "4",
                "company": "Entreprise",
                "person": "Marc Delaunay",
                "status": "Prospect",
                "email": "marc.delaunay@startup.fr",
                "role_line": "Offre corporate 12 salariés",
                "deal_value": "1 200 €",
            },
        ]
    else:
        from tools.premium_demo_data import CRM_CONTACTS

        return _with_brand([dict(c) for c in CRM_CONTACTS], brand_name)
    return _with_brand(rows, brand_name)


def contextual_crm_pipeline(
    *,
    vertical: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str]]:
    if vertical == "marketing":
        h = _hints_or_build(hints, prompt, project_type_label)
        camps = _campaign_list(h)
        return [
            {
                "stage": "Prospect",
                "deal": f"« {camps[0]} » · Luxe Retail · 41k€",
                "color": "#6366f1",
            },
            {
                "stage": "Prospect",
                "deal": f"« {camps[2] if len(camps) > 2 else camps[1]} » · leads · 18k€",
                "color": "#6366f1",
            },
            {
                "stage": "Client",
                "deal": f"Retainer « {camps[1] if len(camps) > 1 else camps[0]} » · 24k€/mois",
                "color": "#4ade80",
            },
            {
                "stage": "Perdu",
                "deal": f"« {camps[3] if len(camps) > 3 else 'Display'} » — budget gelé",
                "color": "#f87171",
            },
        ]
    if vertical == "restaurant":
        return [
            {"stage": "Confirmée", "deal": "Samedi 20h30 — 8 couverts terrasse", "color": "#4ade80"},
            {"stage": "En attente", "deal": "Brunch dimanche — allergie gluten", "color": "#6366f1"},
            {"stage": "Confirmée", "deal": "Menu dégustation chef — 4 pers.", "color": "#4ade80"},
            {"stage": "Annulée", "deal": "Groupe entreprise — no-show", "color": "#f87171"},
        ]
    if vertical == "real_estate":
        return [
            {"stage": "Prospect", "deal": "Visite T3 Lyon — Sophie L.", "color": "#6366f1"},
            {"stage": "Prospect", "deal": "Offre studio — Nadia E.", "color": "#6366f1"},
            {"stage": "Client", "deal": "Mandat T4 Villeurbanne — signé", "color": "#4ade80"},
            {"stage": "Perdu", "deal": "Maison Villefranche — mandat expiré", "color": "#f87171"},
        ]
    if vertical == "artisan":
        return [
            {"stage": "À planifier", "deal": "Devis rénovation SDB — Leroy", "color": "#6366f1"},
            {"stage": "En cours", "deal": "Dépannage fuite — Martin", "color": "#4ade80"},
            {"stage": "Terminé", "deal": "Entretien chaudière — Garnier", "color": "#4ade80"},
            {"stage": "Perdu", "deal": "Installation PAC — budget reporté", "color": "#f87171"},
        ]
    if vertical == "beauty":
        return [
            {"stage": "Confirmé", "deal": "Balayage + coupe — Rousseau", "color": "#4ade80"},
            {"stage": "En attente", "deal": "Forfait mariée — essai", "color": "#6366f1"},
            {"stage": "Confirmé", "deal": "Barbe — Rey (mensuel)", "color": "#4ade80"},
            {"stage": "Annulé", "deal": "No-show — créneau 18h", "color": "#f87171"},
        ]
    if vertical == "fitness":
        return [
            {"stage": "Essai", "deal": "Essai 7 jours — Perrin", "color": "#6366f1"},
            {"stage": "Client", "deal": "Pack coaching 10 séances — Benali", "color": "#4ade80"},
            {"stage": "Client", "deal": "Renouvellement annuel — Lemaire", "color": "#4ade80"},
            {"stage": "Perdu", "deal": "Corporate — budget gelé", "color": "#f87171"},
        ]
    from tools.premium_demo_data import CRM_PIPELINE

    return [dict(p) for p in CRM_PIPELINE]


# —— Dashboard ——

def contextual_dashboard_kpis(
    *,
    vertical: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str]]:
    if vertical == "marketing":
        h = _hints_or_build(hints, prompt, project_type_label)
        c0 = _campaign_list(h)[0]
        return [
            {"label": f"Campagne « {c0} »", "value": "CTR 4,2 %", "trend": "+0,8 pt", "up": True},
            {"label": "Leads qualifiés (MQL)", "value": "1 847", "trend": "+22,4 %", "up": True},
            {"label": "ROI média global", "value": "3,8×", "trend": "+0,6 pt", "up": True},
            {"label": "Clics ads (30 j)", "value": "284 120", "trend": "+11,2 %", "up": True},
        ]
    if vertical == "real_estate":
        return [
            {"label": "Mandats actifs", "value": "38", "trend": "+5", "up": True},
            {"label": "Visites planifiées", "value": "64", "trend": "+18 %", "up": True},
            {"label": "Offres en cours", "value": "11", "trend": "-2", "up": False},
            {"label": "CA commissions", "value": "92 400 €", "trend": "+9,1 %", "up": True},
        ]
    if vertical == "restaurant":
        h = _hints_or_build(hints, prompt, project_type_label)
        cuisine = h.cuisine_label or "carte du chef"
        return [
            {"label": "Couvert (semaine)", "value": "1 240", "trend": "+8,3 %", "up": True},
            {"label": "Réservations en ligne", "value": "312", "trend": "+12 %", "up": True},
            {"label": f"Ticket moyen ({cuisine})", "value": "48,90 €", "trend": "+2,1 %", "up": True},
            {"label": "Taux no-show", "value": "4,2 %", "trend": "-0,8 pt", "up": True},
        ]
    if vertical == "artisan":
        return [
            {"label": "Interventions (7 j)", "value": "46", "trend": "+6", "up": True},
            {"label": "Devis envoyés", "value": "19", "trend": "+12 %", "up": True},
            {"label": "Taux conversion devis", "value": "38 %", "trend": "+4 pt", "up": True},
            {"label": "CA main-d'œuvre", "value": "14 850 €", "trend": "+7,2 %", "up": True},
        ]
    if vertical == "beauty":
        return [
            {"label": "RDV (semaine)", "value": "128", "trend": "+9 %", "up": True},
            {"label": "Taux remplissage", "value": "92 %", "trend": "+3 pt", "up": True},
            {"label": "Panier moyen", "value": "58,40 €", "trend": "+1,8 %", "up": True},
            {"label": "No-show", "value": "3,1 %", "trend": "-0,4 pt", "up": True},
        ]
    if vertical == "fitness":
        return [
            {"label": "Adhérents actifs", "value": "742", "trend": "+21", "up": True},
            {"label": "Taux rétention", "value": "87 %", "trend": "+2 pt", "up": True},
            {"label": "Cours collectifs", "value": "64", "trend": "+8", "up": True},
            {"label": "Upsell coaching", "value": "16,2 %", "trend": "+1,1 pt", "up": True},
        ]
    from tools.premium_demo_data import DASHBOARD_KPIS

    return [dict(k) for k in DASHBOARD_KPIS]


def contextual_dashboard_chart(*, vertical: str) -> list[dict[str, str | int]]:
    if vertical == "marketing":
        return [
            {"month": "Jan", "height": 38, "label": "Clics"},
            {"month": "Fév", "height": 52, "label": "Clics"},
            {"month": "Mar", "height": 61, "label": "Clics"},
            {"month": "Avr", "height": 74, "label": "Clics"},
            {"month": "Mai", "height": 82, "label": "Clics"},
            {"month": "Juin", "height": 95, "label": "Clics"},
        ]
    if vertical == "real_estate":
        return [
            {"month": "Jan", "height": 35},
            {"month": "Fév", "height": 42},
            {"month": "Mar", "height": 58},
            {"month": "Avr", "height": 65},
            {"month": "Mai", "height": 71},
            {"month": "Juin", "height": 88},
        ]
    if vertical == "artisan":
        return [
            {"month": "Jan", "height": 44},
            {"month": "Fév", "height": 49},
            {"month": "Mar", "height": 61},
            {"month": "Avr", "height": 58},
            {"month": "Mai", "height": 72},
            {"month": "Juin", "height": 83},
        ]
    if vertical == "beauty":
        return [
            {"month": "Jan", "height": 52},
            {"month": "Fév", "height": 56},
            {"month": "Mar", "height": 63},
            {"month": "Avr", "height": 70},
            {"month": "Mai", "height": 78},
            {"month": "Juin", "height": 90},
        ]
    if vertical == "fitness":
        return [
            {"month": "Jan", "height": 48},
            {"month": "Fév", "height": 54},
            {"month": "Mar", "height": 57},
            {"month": "Avr", "height": 69},
            {"month": "Mai", "height": 76},
            {"month": "Juin", "height": 88},
        ]
    from tools.premium_demo_data import DASHBOARD_CHART

    return [dict(b) for b in DASHBOARD_CHART]


def contextual_dashboard_sectors(
    *,
    vertical: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str]]:
    if vertical == "marketing":
        h = _hints_or_build(hints, prompt, project_type_label)
        camps = _campaign_list(h)
        return [
            {
                "sector": f"SEA — {camps[0]}",
                "revenue": "48 200 €",
                "growth": "+24 %",
                "share": "38 %",
            },
            {
                "sector": f"Social — {camps[1] if len(camps) > 1 else 'Ads'}",
                "revenue": "31 400 €",
                "growth": "+19 %",
                "share": "25 %",
            },
            {
                "sector": "Email nurturing",
                "revenue": "22 800 €",
                "growth": "+11 %",
                "share": "18 %",
            },
            {
                "sector": f"Retargeting — {camps[3] if len(camps) > 3 else 'panier'}",
                "revenue": "18 050 €",
                "growth": "+8 %",
                "share": "19 %",
            },
        ]
    if vertical == "restaurant":
        return [
            {"sector": "Service midi", "revenue": "18 400 €", "growth": "+9 %", "share": "35 %"},
            {"sector": "Service soir", "revenue": "24 100 €", "growth": "+14 %", "share": "46 %"},
            {"sector": "Bar & cocktails", "revenue": "6 200 €", "growth": "+6 %", "share": "12 %"},
            {"sector": "Événements privés", "revenue": "3 800 €", "growth": "+21 %", "share": "7 %"},
        ]
    if vertical == "real_estate":
        return [
            {"sector": "Vente résidentielle", "revenue": "52 100 €", "growth": "+14 %", "share": "42 %"},
            {"sector": "Location", "revenue": "28 600 €", "growth": "+9 %", "share": "23 %"},
            {"sector": "Investissement", "revenue": "24 200 €", "growth": "+21 %", "share": "20 %"},
            {"sector": "Neuf & promoteurs", "revenue": "18 900 €", "growth": "+6 %", "share": "15 %"},
        ]
    if vertical == "artisan":
        return [
            {"sector": "Dépannage urgent", "revenue": "6 300 €", "growth": "+12 %", "share": "34 %"},
            {"sector": "Rénovation SDB", "revenue": "4 850 €", "growth": "+18 %", "share": "26 %"},
            {"sector": "Chauffage & ECS", "revenue": "5 120 €", "growth": "+7 %", "share": "28 %"},
            {"sector": "Contrats entretien", "revenue": "2 150 €", "growth": "+4 %", "share": "12 %"},
        ]
    if vertical == "beauty":
        return [
            {"sector": "Coupe & brushing", "revenue": "7 400 €", "growth": "+8 %", "share": "38 %"},
            {"sector": "Coloration", "revenue": "5 900 €", "growth": "+11 %", "share": "30 %"},
            {"sector": "Barbier", "revenue": "3 100 €", "growth": "+6 %", "share": "16 %"},
            {"sector": "Soins & beauté", "revenue": "3 000 €", "growth": "+14 %", "share": "16 %"},
        ]
    if vertical == "fitness":
        return [
            {"sector": "Abonnements", "revenue": "24 600 €", "growth": "+9 %", "share": "62 %"},
            {"sector": "Coaching", "revenue": "8 200 €", "growth": "+16 %", "share": "21 %"},
            {"sector": "Cours collectifs", "revenue": "4 300 €", "growth": "+7 %", "share": "11 %"},
            {"sector": "Boutique", "revenue": "2 200 €", "growth": "+5 %", "share": "6 %"},
        ]
    from tools.premium_demo_data import DASHBOARD_SECTORS

    return [dict(s) for s in DASHBOARD_SECTORS]


# —— Facturation ——

def contextual_invoices(
    *,
    vertical: str,
    brand_name: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str | float | int]]:
    if vertical == "marketing":
        return [
            {
                "id": "2026-2101",
                "number": "FAC-2026-2101",
                "client": f"Campagne SEA — {brand_name or 'Pulse Agency'}",
                "ht": 8400.0,
                "status": "Payée",
                "badge_class": "cf-badge",
            },
            {
                "id": "2026-2102",
                "number": "FAC-2026-2102",
                "client": "Retainer social ads — Luxe Retail",
                "ht": 6200.0,
                "status": "En attente",
                "badge_class": "cf-badge cf-badge-pending",
            },
            {
                "id": "2026-2103",
                "number": "FAC-2026-2103",
                "client": "Lead gen GreenMobility",
                "ht": 3900.0,
                "status": "En retard",
                "badge_class": "cf-badge cf-badge-overdue",
            },
        ]
    if vertical == "real_estate":
        return [
            {
                "id": "2026-3101",
                "number": "FAC-2026-3101",
                "client": "Commission vente T4 — Villeurbanne",
                "ht": 12360.0,
                "status": "Payée",
                "badge_class": "cf-badge",
            },
            {
                "id": "2026-3102",
                "number": "FAC-2026-3102",
                "client": f"Honoraires mandat — {brand_name or 'Habitat Plus'}",
                "ht": 4800.0,
                "status": "En attente",
                "badge_class": "cf-badge cf-badge-pending",
            },
        ]
    if vertical == "artisan":
        return [
            {
                "id": "2026-4101",
                "number": "FAC-2026-4101",
                "client": "Dépannage fuite — Sophie Martin",
                "ht": 241.67,
                "status": "Payée",
                "badge_class": "cf-badge",
            },
            {
                "id": "2026-4102",
                "number": "FAC-2026-4102",
                "client": "Rénovation salle de bain — devis",
                "ht": 5666.67,
                "status": "En attente",
                "badge_class": "cf-badge cf-badge-pending",
            },
            {
                "id": "2026-4103",
                "number": "FAC-2026-4103",
                "client": "Entretien chaudière — Philippe Garnier",
                "ht": 150.00,
                "status": "En retard",
                "badge_class": "cf-badge cf-badge-overdue",
            },
        ]
    if vertical == "beauty":
        return [
            {
                "id": "2026-5101",
                "number": "FAC-2026-5101",
                "client": "Balayage + coupe — Camille Rousseau",
                "ht": 120.83,
                "status": "Payée",
                "badge_class": "cf-badge",
            },
            {
                "id": "2026-5102",
                "number": "FAC-2026-5102",
                "client": "Forfait mariée — acompte",
                "ht": 120.00,
                "status": "En attente",
                "badge_class": "cf-badge cf-badge-pending",
            },
        ]
    if vertical == "fitness":
        return [
            {
                "id": "2026-6101",
                "number": "FAC-2026-6101",
                "client": "Abonnement annuel — Sophie Lemaire",
                "ht": 350.00,
                "status": "Payée",
                "badge_class": "cf-badge",
            },
            {
                "id": "2026-6102",
                "number": "FAC-2026-6102",
                "client": "Pack coaching 10 séances — Inès Benali",
                "ht": 408.33,
                "status": "En attente",
                "badge_class": "cf-badge cf-badge-pending",
            },
        ]
    from tools.premium_demo_data import INVOICES

    return [dict(i) for i in INVOICES]


# —— Landing ——

def contextual_landing_features(
    *,
    vertical: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> tuple[str, ...]:
    if vertical == "marketing":
        h = _hints_or_build(hints, prompt, project_type_label)
        c0 = _campaign_list(h)[0]
        return (
            f"Pilotage campagnes (« {c0} », SEA, social, email)",
            "Attribution leads → ROI et CPA en temps réel",
            "Rapports clics, CTR, conversions et MQL exportables",
        )
    if vertical == "restaurant":
        h = _hints_or_build(hints, prompt, project_type_label)
        cuisine = h.cuisine_label or "cuisine de saison"
        return (
            f"Réservations en ligne et plan de salle ({cuisine})",
            "Carte digitale, allergènes et accords mets-vins",
            "Stats couverts, ticket moyen et no-show en direct",
        )
    if vertical == "real_estate":
        return (
            "Fiches biens et mandats centralisés",
            "Planning visites et relances acheteurs",
            "Estimations et documents conformes",
        )
    if vertical == "health":
        return (
            "Prise de rendez-vous et rappels automatiques",
            "Dossiers patients et consentements RGPD",
            "Planning équipe et optimisation des créneaux",
        )
    if vertical == "artisan":
        return (
            "Demandes d’intervention et planning en temps réel",
            "Devis/Factures en 1 clic + signatures",
            "Suivi chantiers, photos et rapports client",
        )
    if vertical == "beauty":
        return (
            "Réservations en ligne + rappels SMS/email",
            "Catalogue prestations, forfaits et fidélité",
            "Gestion équipe, cabines et stocks produits",
        )
    if vertical == "fitness":
        return (
            "Planning cours collectifs + listes d’attente",
            "Abonnements, paiements et relances",
            "Suivi progression + coaching personnalisé",
        )
    from tools.premium_demo_data import LANDING_FEATURES

    return LANDING_FEATURES


def contextual_landing_testimonials(*, vertical: str) -> list[dict[str, str]]:
    if vertical == "marketing":
        return [
            {
                "quote": "Nos campagnes SEA et social sont enfin dans un seul tableau : +31 % de leads qualifiés en 8 semaines.",
                "author": "Camille Rousseau",
                "role": "Directrice acquisition, Pulse Agency",
            },
            {
                "quote": "Le suivi ROI par canal nous a évité deux budgets gaspillés sur le display.",
                "author": "Marc Delaunay",
                "role": "CMO, Luxe Retail Group",
            },
        ]
    if vertical == "real_estate":
        return [
            {
                "quote": "Les mandats et visites sont synchronisés : nous signons 20 % plus vite sur les biens premium.",
                "author": "Sophie Lemaire",
                "role": "Directrice d'agence, Habitat Plus",
            },
            {
                "quote": "Mes acheteurs reçoivent les créneaux de visite sans relance manuelle.",
                "author": "Philippe Garnier",
                "role": "Agent senior, Villeurbanne",
            },
        ]
    if vertical == "restaurant":
        return [
            {
                "quote": "La prise de réservation a réduit les no-shows et on optimise enfin le plan de salle.",
                "author": "Élodie Marchand",
                "role": "Gérante, brasserie",
            },
            {
                "quote": "On a un vrai suivi des couverts + ticket moyen — la marge s’est améliorée dès le 1er mois.",
                "author": "Antoine Leroy",
                "role": "Chef, bistrot",
            },
        ]
    if vertical == "health":
        return [
            {
                "quote": "Les rappels automatiques ont divisé par deux les RDV manqués.",
                "author": "Dr. Sophie Bernard",
                "role": "Médecin généraliste",
            },
            {
                "quote": "Le planning équipe est enfin lisible et on gagne du temps à l’accueil.",
                "author": "Marc Delaunay",
                "role": "Directeur de clinique",
            },
        ]
    if vertical == "artisan":
        return [
            {
                "quote": "Devis et factures partent en 2 minutes, et le client signe sur mobile.",
                "author": "Philippe Garnier",
                "role": "Artisan chauffagiste",
            },
            {
                "quote": "On a un suivi chantier clair (photos, étapes) : zéro malentendu.",
                "author": "Julie Leroy",
                "role": "Particulier — rénovation",
            },
        ]
    if vertical == "beauty":
        return [
            {
                "quote": "Le remplissage du planning a augmenté et les clientes reçoivent les rappels automatiquement.",
                "author": "Camille Rousseau",
                "role": "Manager salon",
            },
            {
                "quote": "L’encaissement est plus fluide et la fidélité se gère sans effort.",
                "author": "Nadia El Amrani",
                "role": "Coiffeuse",
            },
        ]
    if vertical == "fitness":
        return [
            {
                "quote": "Les inscriptions aux cours sont simples, et les listes d’attente remplissent les créneaux.",
                "author": "Julien Perrin",
                "role": "Coach sportif",
            },
            {
                "quote": "Les relances d’abonnement ont stabilisé la rétention.",
                "author": "Sophie Lemaire",
                "role": "Manager club",
            },
        ]
    from tools.premium_demo_data import LANDING_TESTIMONIALS

    return [dict(t) for t in LANDING_TESTIMONIALS]


# —— Tâches seed ——

def contextual_tasks(
    template: str,
    *,
    vertical: str,
    prompt: str,
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> tuple[tuple[str, bool], ...]:
    lower = prompt.lower()
    if vertical == "marketing":
        h = _hints_or_build(hints, prompt, project_type_label)
        camps = _campaign_list(h)
        if template in ("dashboard", "saas_dashboard"):
            return (
                (f"Consolider le ROI — campagne « {camps[0]} »", False),
                ("Valider le rapport leads / clics / CTR hebdo", False),
                (f"Brief créa — « {camps[1] if len(camps) > 1 else camps[0]} »", True),
                ("Ajuster les enchères SEA mobile (+12 % clics)", False),
            )
        if template == "crm":
            return (
                ("Qualifier les leads salon e-commerce", False),
                ("Relancer les prospects campagne GreenMobility", False),
                ("Préparer le pipeline retainer clients", True),
                ("Mettre à jour les scores MQL des comptes actifs", False),
            )
        if template == "landing":
            return (
                ("Finaliser le hero « agence performance »", False),
                ("Ajuster les CTA vers le formulaire leads", False),
                ("Publier la landing campagne été", True),
                ("Brancher le pixel conversion sur les clics", False),
            )
    if vertical == "real_estate":
        if template == "crm":
            return (
                ("Planifier les visites du week-end (3 mandats)", False),
                ("Relancer les acheteurs T3 Lyon 6e", False),
                ("Mettre à jour les estimations des biens en cours", True),
                ("Préparer les compromis en attente de signature", False),
            )
        if template in ("dashboard", "saas_dashboard"):
            return (
                ("Synthèse mandats actifs vs objectifs trimestre", False),
                ("Valider le tableau des visites de la semaine", False),
                ("Exporter le rapport commissions par agence", True),
                ("Alerter sur les mandats expirant sous 15 jours", False),
            )
    if vertical == "restaurant" or "restaurant" in lower:
        h_rest = _hints_or_build(hints, prompt, project_type_label)
        cuisine = h_rest.cuisine_label or "carte du chef"
        tpl = template
        if tpl == "reservation":
            return (
                ("Bloquer la table 14 pour le groupe 8 couverts (20h30)", False),
                ("Relancer réservation brunch — allergie gluten", False),
                ("Synchroniser couverts avec le planning cuisine", True),
                ("Préparer le menu dégustation du chef", False),
            )
        if tpl == "crm":
            return (
                ("Confirmer dégustation presse — menu 5 services", False),
                ("Commander livraison producteurs (mardi matin)", False),
                ("Mettre à jour fiches clients habitués salle", True),
                (f"Valider la carte saison — {cuisine}", False),
            )
        if tpl in ("dashboard", "saas_dashboard"):
            return (
                ("Analyser le ticket moyen service soir vs midi", False),
                ("Réduire le taux no-show du week-end", False),
                ("Publier les stats couverts à l'équipe", True),
                ("Ajuster les créneaux réservation 19h–21h", False),
            )
        return (
            ("Confirmer les réservations du samedi soir", False),
            (f"Mettre à jour la carte desserts — {cuisine}", False),
            ("Commander les produits frais au marché", True),
            ("Brief équipe salle sur les accords mets-vins", False),
        )
    if vertical == "artisan":
        if template == "crm":
            return (
                ("Qualifier les demandes d’intervention (24h)", False),
                ("Envoyer le devis rénovation SDB (PDF)", False),
                ("Planifier les interventions semaine prochaine", True),
                ("Relancer acompte sur devis en attente", False),
            )
        if template in ("dashboard", "saas_dashboard"):
            return (
                ("Suivre le taux conversion devis → interventions", False),
                ("Analyser les urgences week-end (temps moyen)", False),
                ("Exporter le rapport CA main-d'œuvre", True),
                ("Optimiser la tournée (trajets + temps)", False),
            )
        return (
            ("Mettre à jour le planning interventions", False),
            ("Préparer les pièces chantier", False),
            ("Envoyer photos avant/après au client", True),
            ("Finaliser la facture d’intervention", False),
        )
    if vertical == "beauty":
        if template == "reservation":
            return (
                ("Confirmer les RDV de demain (rappels)", False),
                ("Bloquer 1h pour coloration longue", False),
                ("Mettre à jour le catalogue prestations", True),
                ("Relancer les no-show récents", False),
            )
        return (
            ("Préparer les créneaux week-end", False),
            ("Mettre à jour la fiche cliente fidélité", False),
            ("Commander produits coloration", True),
            ("Publier le planning équipe", False),
        )
    if vertical == "fitness":
        if template == "reservation":
            return (
                ("Ouvrir les inscriptions cours du samedi", False),
                ("Gérer la liste d’attente HIIT", False),
                ("Planifier les coachings 1:1", True),
                ("Relancer les essais 7 jours", False),
            )
        return (
            ("Mettre à jour le planning cours collectifs", False),
            ("Analyser la rétention (mensuel)", False),
            ("Lancer une campagne upsell coaching", True),
            ("Préparer onboarding nouveaux adhérents", False),
        )
    return ()


def contextual_reservation_bookings(
    *,
    vertical: str,
    brand_name: str,
    prompt: str = "",
    project_type_label: str = "",
    hints: PromptSeedHints | None = None,
) -> list[dict[str, str | int]]:
    """Créneaux contextualisés (restaurant/beauty/fitness), sinon données premium par défaut."""
    if vertical not in ("restaurant", "beauty", "fitness"):
        from tools.premium_demo_data import RESERVATION_SLOTS
        return [dict(b) for b in RESERVATION_SLOTS]

    h = _hints_or_build(hints, prompt, project_type_label)
    venue = brand_name or h.brand_name
    if vertical == "beauty":
        return [
            {"id": "1", "date": "26 mai 2026", "slot": "10:00", "name": "Camille Rousseau", "covers": 1, "status": "Confirmée", "note": "Balayage + coupe (2h)"},
            {"id": "2", "date": "26 mai 2026", "slot": "14:30", "name": "Nadia El Amrani", "covers": 1, "status": "En attente", "note": "Essai mariée (1h)"},
            {"id": "3", "date": "27 mai 2026", "slot": "18:00", "name": "Thomas Rey", "covers": 1, "status": "Confirmée", "note": f"Barbier — {venue}"},
            {"id": "4", "date": "27 mai 2026", "slot": "19:30", "name": "Sophie Bernard", "covers": 1, "status": "Annulée", "note": "No-show — reprogrammation"},
        ]
    if vertical == "fitness":
        return [
            {"id": "1", "date": "26 mai 2026", "slot": "07:30", "name": "Cours HIIT", "covers": 18, "status": "Confirmée", "note": "Liste d'attente 4"},
            {"id": "2", "date": "26 mai 2026", "slot": "12:15", "name": "Pilates", "covers": 12, "status": "Confirmée", "note": "Niveau intermédiaire"},
            {"id": "3", "date": "27 mai 2026", "slot": "18:30", "name": "Cross-training", "covers": 16, "status": "En attente", "note": "2 places restantes"},
            {"id": "4", "date": "27 mai 2026", "slot": "20:00", "name": "Coaching 1:1", "covers": 1, "status": "Confirmée", "note": f"Objectif renfo — {venue}"},
        ]
    return [
        {
            "id": "1",
            "date": "26 mai 2026",
            "slot": "12:30",
            "name": "Élodie Marchand",
            "covers": 4,
            "status": "Confirmée",
            "note": f"Menu du jour — {h.cuisine_label or 'terrasse'}",
        },
        {
            "id": "2",
            "date": "26 mai 2026",
            "slot": "19:30",
            "name": "Groupe entreprise",
            "covers": 8,
            "status": "Confirmée",
            "note": f"Accord mets-vins — {venue}",
        },
        {
            "id": "3",
            "date": "27 mai 2026",
            "slot": "13:00",
            "name": "Thomas Leroy",
            "covers": 2,
            "status": "En attente",
            "note": "Allergie gluten — plat dédié chef",
        },
        {
            "id": "4",
            "date": "27 mai 2026",
            "slot": "20:30",
            "name": "Sophie Bernard",
            "covers": 3,
            "status": "Annulée",
            "note": "No-show — liste d'attente activée",
        },
    ]
