"""Données fictives par type de démo premium (FR)."""

from __future__ import annotations

# —— CRM ——
CRM_CONTACTS: tuple[dict[str, str], ...] = (
    {
        "id": "1",
        "company": "Logis Pro",
        "person": "Jean Dupont",
        "status": "Prospect",
        "email": "jean.dupont@logispro.fr",
        "role_line": "Jean Dupont — Directeur commercial",
        "deal_value": "18 400 €",
    },
    {
        "id": "2",
        "company": "Média Santé",
        "person": "Marie Martin",
        "status": "Client",
        "email": "marie.martin@mediasante.fr",
        "role_line": "Marie Martin — Responsable achats",
        "deal_value": "12 750 €",
    },
    {
        "id": "3",
        "company": "Alpine Retail",
        "person": "Thomas Leroy",
        "status": "Prospect",
        "email": "t.leroy@alpineretail.fr",
        "role_line": "Thomas Leroy — Chef de projet IT",
        "deal_value": "9 200 €",
    },
    {
        "id": "4",
        "company": "FinTech Plus",
        "person": "Sophie Bernard",
        "status": "Perdu",
        "email": "s.bernard@fintechplus.fr",
        "role_line": "Sophie Bernard — COO",
        "deal_value": "—",
    },
)

CRM_PIPELINE: tuple[dict[str, str], ...] = (
    {"stage": "Prospect", "deal": "Jean Dupont · 18k€", "color": "#6366f1"},
    {"stage": "Prospect", "deal": "Thomas Leroy · 9k€", "color": "#6366f1"},
    {"stage": "Client", "deal": "Marie Martin · 12k€", "color": "#4ade80"},
    {"stage": "Perdu", "deal": "Sophie Bernard", "color": "#f87171"},
)

# —— Dashboard analytics ——
DASHBOARD_KPIS: tuple[dict[str, str], ...] = (
    {"label": "CA mensuel", "value": "128 450 €", "trend": "+14,2 %", "up": True},
    {"label": "Commandes", "value": "1 284", "trend": "+9,8 %", "up": True},
    {"label": "Panier moyen", "value": "96,40 €", "trend": "+3,1 %", "up": True},
    {"label": "Marge brute", "value": "38,6 %", "trend": "-0,4 pt", "up": False},
)

DASHBOARD_CHART: tuple[dict[str, str | int], ...] = (
    {"month": "Jan", "height": 42},
    {"month": "Fév", "height": 55},
    {"month": "Mar", "height": 48},
    {"month": "Avr", "height": 72},
    {"month": "Mai", "height": 68},
    {"month": "Juin", "height": 88},
)

DASHBOARD_SECTORS: tuple[dict[str, str], ...] = (
    {"sector": "Retail & e-commerce", "revenue": "42 100 €", "growth": "+18 %", "share": "33 %"},
    {"sector": "Santé & pharma", "revenue": "31 800 €", "growth": "+11 %", "share": "25 %"},
    {"sector": "BTP & industrie", "revenue": "28 200 €", "growth": "+6 %", "share": "22 %"},
    {"sector": "Services B2B", "revenue": "26 350 €", "growth": "+21 %", "share": "20 %"},
)

# —— Facturation ——
INVOICES: tuple[dict[str, str | float | int], ...] = (
    {
        "id": "2026-1042",
        "number": "FAC-2026-1042",
        "client": "Jean Dupont — Logis Pro",
        "ht": 4200.0,
        "status": "Payée",
        "badge_class": "cf-badge",
    },
    {
        "id": "2026-1043",
        "number": "FAC-2026-1043",
        "client": "Marie Martin — Média Santé",
        "ht": 2650.0,
        "status": "En attente",
        "badge_class": "cf-badge cf-badge-pending",
    },
    {
        "id": "2026-1044",
        "number": "FAC-2026-1044",
        "client": "Thomas Leroy — Alpine Retail",
        "ht": 1580.0,
        "status": "En retard",
        "badge_class": "cf-badge cf-badge-overdue",
    },
    {
        "id": "2026-1045",
        "number": "FAC-2026-1045",
        "client": "Sophie Bernard — FinTech Plus",
        "ht": 8900.0,
        "status": "Payée",
        "badge_class": "cf-badge",
    },
)

# —— Réservation ——
RESERVATION_SLOTS: tuple[dict[str, str | int], ...] = (
    {
        "id": "1",
        "date": "24 mai 2026",
        "slot": "12:30",
        "name": "Jean Dupont",
        "covers": 4,
        "status": "Confirmée",
        "note": "Table terrasse — anniversaire",
    },
    {
        "id": "2",
        "date": "24 mai 2026",
        "slot": "19:00",
        "name": "Marie Martin",
        "covers": 2,
        "status": "En attente",
        "note": "Allergie gluten",
    },
    {
        "id": "3",
        "date": "25 mai 2026",
        "slot": "13:00",
        "name": "Thomas Leroy",
        "covers": 6,
        "status": "Confirmée",
        "note": "Menu dégustation",
    },
    {
        "id": "4",
        "date": "25 mai 2026",
        "slot": "20:30",
        "name": "Sophie Bernard",
        "covers": 3,
        "status": "Annulée",
        "note": "No-show précédent",
    },
    {
        "id": "5",
        "date": "26 mai 2026",
        "slot": "12:00",
        "name": "Luc Moreau",
        "covers": 2,
        "status": "Confirmée",
        "note": "Première visite",
    },
)

# —— Landing ——
LANDING_FEATURES: tuple[str, ...] = (
    "Déploiement en 48 h sans friction",
    "Sécurité et conformité RGPD natives",
    "Support prioritaire 7j/7",
)

LANDING_TESTIMONIALS: tuple[dict[str, str], ...] = (
    {
        "quote": "En trois mois, notre taux de conversion a bondi de 28 %. L'équipe adore l'interface.",
        "author": "Jean Dupont",
        "role": "CEO, Logis Pro",
    },
    {
        "quote": "Onboarding fluide, intégrations propres, ROI visible dès le premier trimestre.",
        "author": "Marie Martin",
        "role": "Directrice marketing, Média Santé",
    },
)

# —— TaskFlow (défaut) ——
DEFAULT_PROFESSIONAL_TASKS: tuple[tuple[str, bool], ...] = (
    ("Préparer le comité de direction du mardi", False),
    ("Finaliser le reporting mensuel Q2", False),
    ("Planifier la revue d'équipe produit", True),
    ("Rédiger la note de cadrage partenaire stratégique", False),
    ("Mettre à jour la matrice des risques opérationnels", False),
)

RESERVATION_TASKS: tuple[tuple[str, bool], ...] = (
    ("Confirmer le créneau 19h — Marie Martin (2 couverts)", False),
    ("Libérer la table 12h30 — Jean Dupont (4 couverts)", False),
    ("Relancer réservation en attente — Thomas Leroy", True),
    ("Préparer plan de salle vendredi soir", False),
    ("Synchroniser les disponibilités en ligne", False),
)
