"""
Boîte à outils génération vitrine — palettes sectorielles, snippets UI et médias (photos, icônes, illustrations).
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import get_settings, plain_secret_str
from cache import ttl_cache
from security.llm_secrets import get_effective_llm_key, get_effective_llm_key_for_http
from tools.codegen_service import _parse_json_response, _utf8_json_body
from tools.toolbox_media import (
    ToolboxIcon,
    ToolboxIllustration,
    ToolboxPhoto,
    search_toolbox_icons,
    search_toolbox_illustrations,
    search_toolbox_photos,
)
from tools.toolbox_sectors import SECTEURS, normalize_sector_key as _normalize_sector_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["toolbox"])

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"
TOOLBOX_TEMP_DIR = Path(__file__).resolve().parent.parent / "temp"
MAX_TOOLBOX_IMAGE_BYTES = 20 * 1024 * 1024
TOOLBOX_TEMP_FILENAME_RE = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.jpe?g$",
    re.IGNORECASE,
)

SCHEMA_ORG_TYPE_BY_SECTOR: dict[str, str] = {
    "restauration": "Restaurant",
    "nautisme": "SportsActivityLocation",
    "immobilier": "RealEstateAgent",
    "sante": "MedicalClinic",
    "artisanat": "HomeAndConstructionBusiness",
    "beaute": "BeautySalon",
    "sport": "SportsActivityLocation",
    "technologie": "ProfessionalService",
    "education": "EducationalOrganization",
    "commerce": "Store",
}

SECTOR_LABELS_FR: dict[str, str] = {
    "restauration": "restauration / restaurant",
    "nautisme": "nautisme / yachting",
    "immobilier": "immobilier",
    "sante": "santé / bien-être",
    "artisanat": "artisanat",
    "beaute": "beauté / esthétique",
    "sport": "sport / fitness",
    "technologie": "technologie / digital",
    "education": "éducation / formation",
    "commerce": "commerce / retail",
}

# ---------------------------------------------------------------------------
# Modèles de réponse
# ---------------------------------------------------------------------------


class SectorPalette(BaseModel):
    primary: str = Field(description="Couleur principale (#hex)")
    secondary: str
    accent: str


class SectorTypography(BaseModel):
    heading: str = Field(description="Google Font pour les titres")
    body: str = Field(description="Google Font pour le corps de texte")


class SectorData(BaseModel):
    nom: str
    palette: SectorPalette
    typo: SectorTypography
    composants: list[str]
    mots_cles_visuels: list[str]


class SecteursResponse(BaseModel):
    secteurs: list[SectorData]


class ComposantEntry(BaseModel):
    id: str
    label: str
    description: str
    categorie: str
    snippet: str
    dependances: list[str]


class ComposantsResponse(BaseModel):
    composants: list[ComposantEntry]


class ToolboxPhotosResponse(BaseModel):
    query: str
    secteur: str | None = None
    photos: list[ToolboxPhoto]


class ToolboxIconsResponse(BaseModel):
    query: str
    icones: list[ToolboxIcon]


class ToolboxIllustrationsResponse(BaseModel):
    query: str
    illustrations: list[ToolboxIllustration]


class SeoMetaRequest(BaseModel):
    secteur: str = Field(min_length=1, max_length=40)
    nom_entreprise: str = Field(min_length=1, max_length=120)
    ville: str = Field(min_length=1, max_length=80)
    description_courte: str = Field(min_length=1, max_length=400)


class SeoMetaResponse(BaseModel):
    title: str
    meta_description: str
    og_title: str
    og_description: str
    keywords: list[str]
    schema_org: dict[str, Any]


class CompressImageRequest(BaseModel):
    image_url: str = Field(min_length=10, max_length=2000)


class CompressImageResponse(BaseModel):
    url: str
    filename: str
    width: int
    height: int
    size_bytes: int


def _sector_to_model(key: str, data: dict[str, Any]) -> SectorData:
    return SectorData(
        nom=key,
        palette=SectorPalette(**data["palette"]),
        typo=SectorTypography(**data["typo"]),
        composants=list(data["composants"]),
        mots_cles_visuels=list(data["mots_cles_visuels"]),
    )


# ---------------------------------------------------------------------------
# Bibliothèque de composants (snippets shadcn/ui + Framer Motion)
# ---------------------------------------------------------------------------

def _snippet(
    component_name: str,
    body: str,
) -> str:
    return (
        '"use client";\n\n'
        'import { motion } from "framer-motion";\n'
        'import { Button } from "@/components/ui/button";\n'
        'import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";\n\n'
        f"export function {component_name}() {{\n"
        f"{body}\n"
        "}\n"
    )


COMPOSANTS: dict[str, dict[str, Any]] = {
    "hero": {
        "label": "Hero",
        "description": "Bannière d'accueil plein écran avec animation d'entrée.",
        "categorie": "layout",
        "dependances": ["framer-motion", "@/components/ui/button"],
        "snippet": _snippet(
            "HeroSection",
            """  return (
    <motion.section
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.65, ease: "easeOut" }}
      className="relative flex min-h-[85vh] flex-col items-center justify-center px-6 text-center"
    >
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="mb-4 text-sm font-medium uppercase tracking-widest text-primary"
      >
        Bienvenue
      </motion.span>
      <motion.h1
        className="max-w-4xl text-4xl font-bold tracking-tight md:text-6xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
      >
        Votre titre principal ici
      </motion.h1>
      <motion.p
        className="mt-6 max-w-2xl text-lg text-muted-foreground"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.35 }}
      >
        Sous-titre qui présente votre proposition de valeur en une phrase claire.
      </motion.p>
      <motion.div
        className="mt-10 flex flex-wrap justify-center gap-4"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
      >
        <Button size="lg">Découvrir</Button>
        <Button size="lg" variant="outline">
          Nous contacter
        </Button>
      </motion.div>
    </motion.section>
  );""",
        ),
    },
    "menu": {
        "label": "Menu / Carte",
        "description": "Grille de plats ou services avec cartes animées.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "MenuSection",
            """  const items = [
    { title: "Entrée du chef", price: "12€", desc: "Description courte du plat." },
    { title: "Plat signature", price: "24€", desc: "Description courte du plat." },
    { title: "Dessert maison", price: "9€", desc: "Description courte du plat." },
  ];

  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <motion.h2
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-10 text-center text-3xl font-bold"
      >
        Notre carte
      </motion.h2>
      <div className="grid gap-6 md:grid-cols-3">
        {items.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
          >
            <Card className="h-full border-border/60">
              <CardHeader className="flex flex-row items-baseline justify-between">
                <CardTitle className="text-lg">{item.title}</CardTitle>
                <span className="font-semibold text-primary">{item.price}</span>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "testimonials": {
        "label": "Témoignages",
        "description": "Avis clients en cartes avec apparition au scroll.",
        "categorie": "social-proof",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "TestimonialsSection",
            """  const reviews = [
    { name: "Marie L.", quote: "Service impeccable, je recommande vivement." },
    { name: "Thomas D.", quote: "Une expérience au-delà de nos attentes." },
    { name: "Sophie R.", quote: "Professionnalisme et qualité constante." },
  ];

  return (
    <section className="bg-muted/40 px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-12 text-center text-3xl font-bold">Ils nous font confiance</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {reviews.map((r, i) => (
            <motion.div
              key={r.name}
              initial={{ opacity: 0, scale: 0.96 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className="h-full p-6">
                <p className="text-muted-foreground">&ldquo;{r.quote}&rdquo;</p>
                <p className="mt-4 font-medium">{r.name}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );""",
        ),
    },
    "contact": {
        "label": "Contact",
        "description": "Formulaire de contact avec champs shadcn et animation.",
        "categorie": "conversion",
        "dependances": [
            "framer-motion",
            "@/components/ui/button",
            "@/components/ui/input",
            "@/components/ui/textarea",
        ],
        "snippet": _snippet(
            "ContactSection",
            """  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="mx-auto max-w-xl px-6 py-20"
    >
      <h2 className="mb-8 text-center text-3xl font-bold">Contactez-nous</h2>
      <form className="space-y-4">
        <input
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          placeholder="Votre nom"
          type="text"
        />
        <input
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          placeholder="Email"
          type="email"
        />
        <textarea
          className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="Votre message"
        />
        <Button type="submit" className="w-full">
          Envoyer
        </Button>
      </form>
    </motion.section>
  );""",
        ),
    },
    "features": {
        "label": "Fonctionnalités",
        "description": "Grille de points forts avec icônes et motion stagger.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "FeaturesSection",
            """  const features = [
    { title: "Rapide", desc: "Mise en place en quelques jours." },
    { title: "Fiable", desc: "Infrastructure stable et sécurisée." },
    { title: "Sur mesure", desc: "Adapté à votre activité." },
  ];

  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="mb-12 text-center text-3xl font-bold">Pourquoi nous choisir</h2>
      <div className="grid gap-8 md:grid-cols-3">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>{f.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{f.desc}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "gallery": {
        "label": "Galerie",
        "description": "Grille d'images responsive avec effet hover.",
        "categorie": "media",
        "dependances": ["framer-motion"],
        "snippet": _snippet(
            "GallerySection",
            """  const images = Array.from({ length: 6 }, (_, i) => ({
    id: i + 1,
    alt: `Photo ${i + 1}`,
  }));

  return (
    <section className="px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Galerie</h2>
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-4 md:grid-cols-3">
        {images.map((img, i) => (
          <motion.div
            key={img.id}
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.03 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}
            className="aspect-square rounded-lg bg-muted"
            role="img"
            aria-label={img.alt}
          />
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "pricing": {
        "label": "Tarifs",
        "description": "Plans tarifaires en cartes comparatives.",
        "categorie": "conversion",
        "dependances": ["framer-motion", "@/components/ui/button", "@/components/ui/card"],
        "snippet": _snippet(
            "PricingSection",
            """  const plans = [
    { name: "Essentiel", price: "29€", features: ["Fonction A", "Support email"] },
    { name: "Pro", price: "79€", features: ["Tout Essentiel", "Support prioritaire"], highlight: true },
    { name: "Entreprise", price: "Sur devis", features: ["Sur mesure", "SLA dédié"] },
  ];

  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="mb-12 text-center text-3xl font-bold">Nos offres</h2>
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className={plan.highlight ? "border-primary shadow-lg" : ""}>
              <CardHeader>
                <CardTitle>{plan.name}</CardTitle>
                <p className="text-3xl font-bold">{plan.price}</p>
              </CardHeader>
              <CardContent className="space-y-2">
                {plan.features.map((f) => (
                  <p key={f} className="text-sm text-muted-foreground">
                    ✓ {f}
                  </p>
                ))}
                <Button className="mt-4 w-full" variant={plan.highlight ? "default" : "outline"}>
                  Choisir
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "cta": {
        "label": "Appel à l'action",
        "description": "Bandeau de conversion avec bouton principal.",
        "categorie": "conversion",
        "dependances": ["framer-motion", "@/components/ui/button"],
        "snippet": _snippet(
            "CtaSection",
            """  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="mx-6 my-16 rounded-2xl bg-primary px-8 py-16 text-center text-primary-foreground"
    >
      <h2 className="text-3xl font-bold">Prêt à commencer ?</h2>
      <p className="mx-auto mt-4 max-w-xl opacity-90">
        Rejoignez des centaines de clients satisfaits dès aujourd&apos;hui.
      </p>
      <Button size="lg" variant="secondary" className="mt-8">
        Demander un devis
      </Button>
    </motion.section>
  );""",
        ),
    },
    "faq": {
        "label": "FAQ",
        "description": "Questions fréquentes avec accordéon animé.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "FaqSection",
            """  const faqs = [
    { q: "Quels sont vos délais ?", a: "En général 2 à 4 semaines selon le projet." },
    { q: "Proposez-vous un accompagnement ?", a: "Oui, du brief à la mise en ligne." },
  ];

  return (
    <section className="mx-auto max-w-3xl px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Questions fréquentes</h2>
      <div className="space-y-4">
        {faqs.map((item, i) => (
          <motion.div
            key={item.q}
            initial={{ opacity: 0, x: -12 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
          >
            <Card className="p-6">
              <h3 className="font-semibold">{item.q}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.a}</p>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "stats": {
        "label": "Statistiques",
        "description": "Chiffres clés animés au scroll.",
        "categorie": "social-proof",
        "dependances": ["framer-motion"],
        "snippet": _snippet(
            "StatsSection",
            """  const stats = [
    { value: "500+", label: "Clients" },
    { value: "98%", label: "Satisfaction" },
    { value: "10 ans", label: "Expérience" },
  ];

  return (
    <section className="border-y bg-muted/30 px-6 py-16">
      <div className="mx-auto grid max-w-4xl grid-cols-3 gap-8 text-center">
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12 }}
          >
            <p className="text-4xl font-bold text-primary">{s.value}</p>
            <p className="mt-2 text-sm text-muted-foreground">{s.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "team": {
        "label": "Équipe",
        "description": "Présentation des membres avec photos et rôles.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "TeamSection",
            """  const members = [
    { name: "Alex Martin", role: "Fondateur" },
    { name: "Julie Chen", role: "Directrice" },
    { name: "Marc Dupont", role: "Expert métier" },
  ];

  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="mb-12 text-center text-3xl font-bold">Notre équipe</h2>
      <div className="grid gap-8 md:grid-cols-3">
        {members.map((m, i) => (
          <motion.div
            key={m.name}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="text-center">
              <div className="mx-auto mb-4 h-24 w-24 rounded-full bg-muted" />
              <CardHeader>
                <CardTitle className="text-lg">{m.name}</CardTitle>
                <p className="text-sm text-muted-foreground">{m.role}</p>
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "newsletter": {
        "label": "Newsletter",
        "description": "Inscription email avec validation visuelle.",
        "categorie": "conversion",
        "dependances": ["framer-motion", "@/components/ui/button", "@/components/ui/input"],
        "snippet": _snippet(
            "NewsletterSection",
            """  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="mx-auto max-w-lg px-6 py-16 text-center"
    >
      <h2 className="text-2xl font-bold">Restez informé</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Recevez nos actualités et offres exclusives.
      </p>
      <form className="mt-6 flex gap-2">
        <input
          type="email"
          placeholder="votre@email.com"
          className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 text-sm"
        />
        <Button type="submit">S&apos;inscrire</Button>
      </form>
    </motion.section>
  );""",
        ),
    },
    "services": {
        "label": "Services",
        "description": "Liste de prestations avec descriptions courtes.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "ServicesSection",
            """  const services = [
    { title: "Conseil", desc: "Accompagnement stratégique personnalisé." },
    { title: "Réalisation", desc: "Exécution clé en main de A à Z." },
    { title: "Suivi", desc: "Maintenance et optimisation continue." },
  ];

  return (
    <section className="px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Nos services</h2>
      <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-3">
        {services.map((s, i) => (
          <motion.div
            key={s.title}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="h-full p-6">
              <h3 className="font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "hours": {
        "label": "Horaires",
        "description": "Tableau des horaires d'ouverture.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "HoursSection",
            """  const hours = [
    { day: "Lun – Ven", time: "9h – 19h" },
    { day: "Samedi", time: "10h – 18h" },
    { day: "Dimanche", time: "Fermé" },
  ];

  return (
    <section className="mx-auto max-w-md px-6 py-16">
      <Card>
        <CardHeader>
          <CardTitle>Horaires d&apos;ouverture</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {hours.map((row, i) => (
            <motion.div
              key={row.day}
              initial={{ opacity: 0, x: -8 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="flex justify-between text-sm"
            >
              <span className="font-medium">{row.day}</span>
              <span className="text-muted-foreground">{row.time}</span>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </section>
  );""",
        ),
    },
    "listings": {
        "label": "Annonces",
        "description": "Grille de biens ou produits avec filtres visuels.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card", "@/components/ui/button"],
        "snippet": _snippet(
            "ListingsSection",
            """  const listings = [
    { title: "Appartement centre-ville", price: "320 000 €", meta: "3 pièces · 72 m²" },
    { title: "Maison avec jardin", price: "485 000 €", meta: "5 pièces · 140 m²" },
  ];

  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="mb-10 text-3xl font-bold">Nos biens</h2>
      <div className="grid gap-6 md:grid-cols-2">
        {listings.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="overflow-hidden">
              <div className="aspect-video bg-muted" />
              <CardContent className="p-4">
                <h3 className="font-semibold">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.meta}</p>
                <p className="mt-2 text-lg font-bold text-primary">{item.price}</p>
                <Button variant="outline" size="sm" className="mt-3">
                  Voir le détail
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "fleet": {
        "label": "Flotte",
        "description": "Présentation de bateaux ou véhicules disponibles.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "FleetSection",
            """  const boats = [
    { name: "Catamaran 42ft", cap: "12 passagers" },
    { name: "Voilier croisière", cap: "8 passagers" },
  ];

  return (
    <section className="px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Notre flotte</h2>
      <div className="mx-auto grid max-w-4xl gap-8 md:grid-cols-2">
        {boats.map((b, i) => (
          <motion.div
            key={b.name}
            initial={{ opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card>
              <div className="aspect-[16/10] bg-muted" />
              <CardHeader>
                <CardTitle>{b.name}</CardTitle>
                <p className="text-sm text-muted-foreground">{b.cap}</p>
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "process": {
        "label": "Processus",
        "description": "Étapes de travail numérotées avec timeline.",
        "categorie": "content",
        "dependances": ["framer-motion"],
        "snippet": _snippet(
            "ProcessSection",
            """  const steps = [
    { n: 1, title: "Brief", desc: "Comprendre votre besoin." },
    { n: 2, title: "Conception", desc: "Proposition et validation." },
    { n: 3, title: "Livraison", desc: "Réalisation et suivi." },
  ];

  return (
    <section className="mx-auto max-w-3xl px-6 py-20">
      <h2 className="mb-12 text-center text-3xl font-bold">Notre méthode</h2>
      <ol className="space-y-8">
        {steps.map((step, i) => (
          <motion.li
            key={step.n}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12 }}
            className="flex gap-6"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
              {step.n}
            </span>
            <div>
              <h3 className="font-semibold">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.desc}</p>
            </div>
          </motion.li>
        ))}
      </ol>
    </section>
  );""",
        ),
    },
    "programs": {
        "label": "Programmes",
        "description": "Offres de formation ou d'entraînement structurées.",
        "categorie": "content",
        "dependances": ["framer-motion", "@/components/ui/card"],
        "snippet": _snippet(
            "ProgramsSection",
            """  const programs = [
    { title: "Initiation", duration: "4 semaines", level: "Débutant" },
    { title: "Perfectionnement", duration: "8 semaines", level: "Intermédiaire" },
  ];

  return (
    <section className="mx-auto max-w-4xl px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Nos programmes</h2>
      <div className="grid gap-6 md:grid-cols-2">
        {programs.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="p-6">
              <h3 className="text-xl font-semibold">{p.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {p.duration} · {p.level}
              </p>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "products": {
        "label": "Produits",
        "description": "Vitrine produits e-commerce en grille.",
        "categorie": "commerce",
        "dependances": ["framer-motion", "@/components/ui/card", "@/components/ui/button"],
        "snippet": _snippet(
            "ProductsSection",
            """  const products = [
    { name: "Produit A", price: "49€" },
    { name: "Produit B", price: "79€" },
    { name: "Produit C", price: "129€" },
  ];

  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="mb-10 text-center text-3xl font-bold">Boutique</h2>
      <div className="grid grid-cols-2 gap-6 md:grid-cols-3">
        {products.map((p, i) => (
          <motion.div
            key={p.name}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
          >
            <Card>
              <div className="aspect-square bg-muted" />
              <CardContent className="p-4">
                <h3 className="font-medium">{p.name}</h3>
                <p className="text-primary font-semibold">{p.price}</p>
                <Button size="sm" className="mt-3 w-full">
                  Ajouter
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );""",
        ),
    },
    "footer": {
        "label": "Pied de page",
        "description": "Footer avec liens, réseaux et copyright.",
        "categorie": "layout",
        "dependances": ["framer-motion"],
        "snippet": _snippet(
            "FooterSection",
            """  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="border-t bg-muted/30 px-6 py-12"
    >
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 md:flex-row">
        <p className="font-semibold">Votre marque</p>
        <nav className="flex gap-6 text-sm text-muted-foreground">
          <a href="#services">Services</a>
          <a href="#contact">Contact</a>
          <a href="#legal">Mentions légales</a>
        </nav>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} Tous droits réservés
        </p>
      </div>
    </motion.footer>
  );""",
        ),
    },
}


def _composant_to_model(comp_id: str, data: dict[str, Any]) -> ComposantEntry:
    return ComposantEntry(
        id=comp_id,
        label=str(data["label"]),
        description=str(data["description"]),
        categorie=str(data["categorie"]),
        snippet=str(data["snippet"]),
        dependances=list(data["dependances"]),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/toolbox/secteurs", response_model=SecteursResponse)
@ttl_cache(seconds=30.0)
async def list_secteurs() -> SecteursResponse:
    """Retourne tous les secteurs avec palette, typo, composants et mots-clés visuels."""
    items = [_sector_to_model(key, data) for key, data in SECTEURS.items()]
    return SecteursResponse(secteurs=items)


@router.get("/toolbox/secteur/{nom}", response_model=SectorData)
async def get_secteur(nom: str) -> SectorData:
    """Retourne les données d'un secteur précis (nom ou alias, ex. santé → sante)."""
    key = _normalize_sector_key(nom)
    data = SECTEURS.get(key)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Secteur inconnu : {nom}. Valeurs : {', '.join(sorted(SECTEURS))}.",
        )
    return _sector_to_model(key, data)


@router.get("/toolbox/composants", response_model=ComposantsResponse)
async def list_composants() -> ComposantsResponse:
    """Bibliothèque complète de blocs UI avec snippets shadcn/ui + Framer Motion."""
    items = [_composant_to_model(cid, data) for cid, data in COMPOSANTS.items()]
    return ComposantsResponse(composants=items)


# ---------------------------------------------------------------------------
# Médias externes (Pexels, Unsplash, Iconify, unDraw)
# ---------------------------------------------------------------------------


def _toolbox_timeout() -> float:
    return get_settings().toolbox_http_timeout_seconds


@router.get("/toolbox/photos", response_model=ToolboxPhotosResponse)
async def get_toolbox_photos(
    query: str = Query(default="", max_length=120),
    secteur: str | None = Query(default=None, max_length=40),
    per_page: int = Query(default=12, ge=1, le=80),
) -> ToolboxPhotosResponse:
    """
    Photos stock — Pexels en priorité ; si moins de 6 résultats, complément Unsplash.
    """
    settings = get_settings()
    if not settings.pexels_configured and not settings.unsplash_configured:
        raise HTTPException(
            status_code=503,
            detail="Aucune clé photo configurée (PEXELS_API_KEY ou UNSPLASH_ACCESS_KEY).",
        )

    effective_query, photos = await search_toolbox_photos(
        query, secteur=secteur, per_page=per_page, settings=settings
    )
    return ToolboxPhotosResponse(
        query=effective_query,
        secteur=secteur.strip() if secteur else None,
        photos=photos,
    )


@router.get("/toolbox/icones", response_model=ToolboxIconsResponse)
async def get_toolbox_icones(
    query: str = Query(default="", max_length=80),
    limit: int = Query(default=24, ge=1, le=999),
) -> ToolboxIconsResponse:
    """Recherche d'icônes via l'API Iconify."""
    effective_query, icones = await search_toolbox_icons(query, limit=limit)
    return ToolboxIconsResponse(query=effective_query, icones=icones)


@router.get("/toolbox/illustrations", response_model=ToolboxIllustrationsResponse)
async def get_toolbox_illustrations(
    query: str = Query(default="", max_length=80),
    limit: int = Query(default=12, ge=1, le=80),
) -> ToolboxIllustrationsResponse:
    """Illustrations unDraw (recherche par mot-clé)."""
    effective_query, illustrations = await search_toolbox_illustrations(query, limit=limit)
    return ToolboxIllustrationsResponse(
        query=effective_query,
        illustrations=illustrations,
    )


# ---------------------------------------------------------------------------
# SEO (DeepSeek) & compression d'images
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[: max_len - 1].rsplit(" ", 1)[0]
    return cut if cut else cleaned[:max_len]


async def _call_deepseek_json(*, system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    api_key = get_effective_llm_key("DEEPSEEK_API_KEY", settings)
    if not api_key:
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY manquante.")

    body, content_headers = _utf8_json_body(
        {
            "model": settings.coremind_deepseek_model,
            "temperature": 0.35,
            "max_tokens": min(settings.coremind_max_output_tokens, 2048),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    )
    timeout = httpx.Timeout(settings.coremind_llm_timeout_seconds, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            DEEPSEEK_CHAT_URL,
            headers={
                "Authorization": f"Bearer {get_effective_llm_key_for_http('DEEPSEEK_API_KEY', settings) or api_key}",
                **content_headers,
            },
            content=body,
        )

    if response.status_code >= 400:
        snippet = response.content.decode("utf-8", errors="replace")[:400]
        raise HTTPException(status_code=502, detail=f"DeepSeek HTTP {response.status_code}: {snippet}")

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if not str(content).strip():
        raise HTTPException(status_code=502, detail="Réponse DeepSeek vide.")
    return _parse_json_response(str(content))


def _normalize_keywords(raw: Any) -> list[str]:
    if isinstance(raw, str):
        parts = [p.strip() for p in re.split(r"[,;]", raw) if p.strip()]
    elif isinstance(raw, list):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    else:
        parts = []
    return parts[:10]


def _build_seo_meta_from_llm(
    data: dict[str, Any],
    *,
    nom_entreprise: str,
    ville: str,
    schema_type: str,
) -> SeoMetaResponse:
    title = _truncate(str(data.get("title") or nom_entreprise), 60)
    meta_description = _truncate(
        str(data.get("meta_description") or data.get("description") or ""),
        155,
    )
    og_title = _truncate(str(data.get("og_title") or title), 70)
    og_description = _truncate(str(data.get("og_description") or meta_description), 200)
    keywords = _normalize_keywords(data.get("keywords"))
    if len(keywords) < 10:
        fallback = [nom_entreprise, ville, schema_type.replace("Business", "").lower()]
        for word in fallback:
            if word and word not in keywords:
                keywords.append(word)
            if len(keywords) >= 10:
                break

    schema_raw = data.get("schema_org")
    if isinstance(schema_raw, str):
        try:
            import json

            schema_org = json.loads(schema_raw)
        except json.JSONDecodeError:
            schema_org = {}
    elif isinstance(schema_raw, dict):
        schema_org = dict(schema_raw)
    else:
        schema_org = {}

    schema_org.setdefault("@context", "https://schema.org")
    schema_org["@type"] = schema_org.get("@type") or schema_type
    schema_org.setdefault("name", nom_entreprise)
    schema_org.setdefault("description", meta_description)
    address = schema_org.get("address")
    if not isinstance(address, dict):
        address = {}
    address.setdefault("@type", "PostalAddress")
    address.setdefault("addressLocality", ville)
    schema_org["address"] = address

    return SeoMetaResponse(
        title=title,
        meta_description=meta_description,
        og_title=og_title,
        og_description=og_description,
        keywords=keywords[:10],
        schema_org=schema_org,
    )


def _compress_image_sync(data: bytes) -> tuple[bytes, int, int]:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")

        width, height = img.size
        if width > 1200:
            height = max(1, int(height * 1200 / width))
            width = 1200
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85, optimize=True)
        return out.getvalue(), width, height


@router.post("/toolbox/seo-meta", response_model=SeoMetaResponse)
async def generate_toolbox_seo_meta(body: SeoMetaRequest) -> SeoMetaResponse:
    """Génère title, meta, Open Graph, mots-clés et JSON-LD via DeepSeek V3."""
    sector_key = _normalize_sector_key(body.secteur)
    sector_label = SECTOR_LABELS_FR.get(sector_key, body.secteur.strip())
    schema_type = SCHEMA_ORG_TYPE_BY_SECTOR.get(sector_key, "LocalBusiness")

    system = (
        "Tu es expert SEO local pour sites vitrines français. "
        "Réponds UNIQUEMENT avec un objet JSON valide, sans markdown."
    )
    user = f"""Génère les métadonnées SEO pour cette entreprise :
- Secteur : {sector_label}
- Nom : {body.nom_entreprise}
- Ville : {body.ville}
- Description : {body.description_courte}

Contraintes strictes :
- title : maximum 60 caractères, accrocheur, inclure la ville si possible
- meta_description : maximum 155 caractères
- og_title et og_description : adaptés au partage social (og_description ≤ 200 car.)
- keywords : tableau de exactement 10 mots-clés français pertinents (courts)
- schema_org : objet JSON-LD schema.org de type {schema_type} (ou LocalBusiness adapté)
  avec name, description, address (PostalAddress + addressLocality), url optionnelle,
  telephone optionnel, sameAs optionnel, areaServed = {body.ville}

JSON attendu :
{{
  "title": "...",
  "meta_description": "...",
  "og_title": "...",
  "og_description": "...",
  "keywords": ["...", ...],
  "schema_org": {{ "@context": "https://schema.org", "@type": "{schema_type}", ... }}
}}"""

    raw = await _call_deepseek_json(system=system, user=user)
    return _build_seo_meta_from_llm(
        raw,
        nom_entreprise=body.nom_entreprise.strip(),
        ville=body.ville.strip(),
        schema_type=schema_type,
    )


@router.post("/toolbox/compress-image", response_model=CompressImageResponse)
async def compress_toolbox_image(body: CompressImageRequest) -> CompressImageResponse:
    """Télécharge, compresse (JPEG 85 %, max 1200 px) et expose une URL locale."""
    image_url = body.image_url.strip()
    if not image_url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="image_url doit être une URL HTTP(S).")

    async with httpx.AsyncClient(
        timeout=_toolbox_timeout(),
        follow_redirects=True,
    ) as client:
        response = await client.get(image_url)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Téléchargement impossible (HTTP {response.status_code}).",
        )
    if len(response.content) > MAX_TOOLBOX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image trop volumineuse (max 20 Mo).")

    try:
        compressed, width, height = await asyncio.to_thread(
            _compress_image_sync,
            response.content,
        )
    except Exception as exc:
        logger.exception("Compression image toolbox")
        raise HTTPException(status_code=400, detail="Image invalide ou format non supporté.") from exc

    TOOLBOX_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    dest = TOOLBOX_TEMP_DIR / filename
    dest.write_bytes(compressed)

    settings = get_settings()
    local_url = f"{settings.backend_public_url.rstrip('/')}/api/toolbox/temp/{filename}"

    return CompressImageResponse(
        url=local_url,
        filename=filename,
        width=width,
        height=height,
        size_bytes=len(compressed),
    )


@router.get("/toolbox/temp/{filename}")
async def serve_toolbox_temp_image(filename: str) -> FileResponse:
    """Sert une image compressée depuis backend/temp/."""
    if not TOOLBOX_TEMP_FILENAME_RE.match(filename):
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    path = (TOOLBOX_TEMP_DIR / filename).resolve()
    try:
        path.relative_to(TOOLBOX_TEMP_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Fichier introuvable.") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    return FileResponse(path, media_type="image/jpeg")
