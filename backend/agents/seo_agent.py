"""
SEOAgent — CyberForge
Injecte automatiquement les balises SEO dans chaque site généré.
Fonctionne sur le HTML final — après GeneratorAI + OpenHands, avant DeployAI.
Zéro appel LLM — injection déterministe basée sur le brief client.
Coût : $0.00
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

SCHEMA_MAP = {
    "plombier": "Plumber",
    "electricien": "Electrician",
    "menuisier": "Carpenter",
    "peintre": "Painter",
    "maçon": "MasonryCleaning",
    "restaurant": "Restaurant",
    "boulangerie": "Bakery",
    "boulanger": "Bakery",
    "café": "CafeOrCoffeeShop",
    "coiffeur": "HairSalon",
    "coiffure": "HairSalon",
    "beauté": "BeautySalon",
    "spa": "DaySpa",
    "médecin": "Physician",
    "dentiste": "Dentist",
    "pharmacie": "Pharmacy",
    "kiné": "MedicalClinic",
    "immobilier": "RealEstateAgent",
    "agence": "ProfessionalService",
    "avocat": "LegalService",
    "comptable": "AccountingService",
    "sport": "SportsActivityLocation",
    "salle de sport": "HealthClub",
    "yoga": "HealthClub",
    "hotel": "Hotel",
    "hôtel": "Hotel",
    "chambre": "BedAndBreakfast",
    "transport": "MovingCompany",
    "garage": "AutoRepair",
    "auto": "AutoRepair",
    "fleuriste": "Florist",
    "bijou": "JewelryStore",
    "mode": "ClothingStore",
    "informatique": "ComputerStore",
    "formation": "EducationalOrganization",
    "école": "School",
    "association": "NGO",
}

META_DESCRIPTIONS = {
    "vitrine": "{client} — {sector} professionnel. Découvrez nos services, réalisations et contactez-nous pour un devis gratuit.",
    "ecommerce": "{client} — Boutique en ligne {sector}. Livraison rapide, paiement sécurisé, satisfaction garantie.",
    "booking": "{client} — Réservez en ligne facilement. {sector} disponible 7j/7. Confirmez votre réservation en quelques clics.",
    "web_app": "{client} — Application {sector} intuitive et performante. Accédez à vos données partout, à tout moment.",
    "crm": "{client} — Gérez votre activité {sector} simplement. CRM professionnel adapté à votre métier.",
}


class SEOAgent:
    """Injecte les balises SEO dans le HTML généré — déterministe, zéro LLM."""

    def inject(
        self,
        html: str,
        client_name: str,
        sector: str = "",
        project_type: str = "vitrine_next",
        city: str = "",
        description: str = "",
        url: str = "",
    ) -> str:
        try:
            html = self._inject_meta_tags(
                html, client_name, sector, project_type, city, description, url
            )
            html = self._inject_schema_org(html, client_name, sector, city, url)
            html = self._inject_og_tags(html, client_name, sector, description, url)
            html = self._ensure_viewport(html)
            html = self._inject_sitemap_comment(html, url)
            logger.info("SEOAgent — injection complète pour %s", client_name)
            return html
        except Exception as e:
            logger.error("SEOAgent error: %s", e)
            return html

    def generate_sitemap(self, url: str, pages: list[dict[str, str]] | None = None) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        base_url = url.rstrip("/")

        default_pages = pages or [
            {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
            {"loc": "/contact", "priority": "0.8", "changefreq": "monthly"},
            {"loc": "/services", "priority": "0.8", "changefreq": "monthly"},
            {"loc": "/a-propos", "priority": "0.6", "changefreq": "monthly"},
        ]

        urls_xml = ""
        for page in default_pages:
            urls_xml += f"""  <url>
    <loc>{base_url}{page['loc']}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{page.get('changefreq', 'monthly')}</changefreq>
    <priority>{page.get('priority', '0.5')}</priority>
  </url>\n"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}</urlset>"""

    def generate_robots_txt(self, url: str) -> str:
        base_url = url.rstrip("/")
        return f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: {base_url}/sitemap.xml"""

    def _inject_meta_tags(
        self,
        html: str,
        client_name: str,
        sector: str,
        project_type: str,
        city: str,
        description: str,
        url: str,
    ) -> str:
        title_parts = [client_name]
        if sector:
            title_parts.append(sector.capitalize())
        if city:
            title_parts.append(city)
        seo_title = " — ".join(title_parts)

        if description:
            meta_desc = description[:160]
        else:
            template_key = self._get_project_key(project_type)
            template = META_DESCRIPTIONS.get(template_key, META_DESCRIPTIONS["vitrine"])
            meta_desc = template.format(
                client=client_name,
                sector=sector or "professionnel",
            )[:160]

        if re.search(r"<title>", html, re.IGNORECASE):
            html = re.sub(
                r"<title>.*?</title>",
                f"<title>{seo_title}</title>",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
        else:
            html = html.replace("<head>", f"<head>\n  <title>{seo_title}</title>")

        html = re.sub(
            r'<meta\s+name=["\']description["\'][^>]*>',
            "",
            html,
            flags=re.IGNORECASE,
        )

        meta_tags = f"""
  <meta name="description" content="{meta_desc}">
  <meta name="robots" content="index, follow">"""

        if url:
            meta_tags += f'\n  <link rel="canonical" href="{url}">'

        html = html.replace("</title>", f"</title>{meta_tags}")
        return html

    def _inject_schema_org(
        self,
        html: str,
        client_name: str,
        sector: str,
        city: str,
        url: str,
    ) -> str:
        schema_type = "LocalBusiness"
        sector_lower = sector.lower() if sector else ""
        for keyword, schema in SCHEMA_MAP.items():
            if keyword in sector_lower:
                schema_type = schema
                break

        schema_data: dict[str, object] = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": client_name,
        }

        if url:
            schema_data["url"] = url
        if city:
            schema_data["address"] = {
                "@type": "PostalAddress",
                "addressLocality": city,
                "addressCountry": "FR",
            }

        schema_json = json.dumps(schema_data, ensure_ascii=False, indent=2)
        schema_script = f"""
  <script type="application/ld+json">
{schema_json}
  </script>"""

        if "</head>" in html:
            html = html.replace("</head>", f"{schema_script}\n</head>")
        else:
            html = html + schema_script

        return html

    def _inject_og_tags(
        self,
        html: str,
        client_name: str,
        sector: str,
        description: str,
        url: str,
    ) -> str:
        og_description = (
            description[:200]
            if description
            else f"{client_name} — {sector or 'Professionnel'}"
        )

        og_tags = f"""
  <meta property="og:type" content="website">
  <meta property="og:title" content="{client_name}">
  <meta property="og:description" content="{og_description}">
  <meta property="og:locale" content="fr_FR">"""

        if url:
            og_tags += f'\n  <meta property="og:url" content="{url}">'

        og_tags += f"""
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{client_name}">
  <meta name="twitter:description" content="{og_description}">"""

        html = re.sub(
            r'<meta\s+property=["\']og:[^"\']*["\'][^>]*>',
            "",
            html,
            flags=re.IGNORECASE,
        )

        if "</head>" in html:
            html = html.replace("</head>", f"{og_tags}\n</head>")

        return html

    def _ensure_viewport(self, html: str) -> str:
        if 'name="viewport"' not in html and "name='viewport'" not in html:
            viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            html = html.replace("<head>", f"<head>\n  {viewport}")
        return html

    def _inject_sitemap_comment(self, html: str, url: str) -> str:
        if not url:
            return html
        comment = f"""<!-- SEO CyberForge
  sitemap.xml : {url}/sitemap.xml
  robots.txt  : {url}/robots.txt
-->"""
        return html.replace("<!DOCTYPE html>", f"<!DOCTYPE html>\n{comment}")

    def _get_project_key(self, project_type: str) -> str:
        mapping = {
            "vitrine_next": "vitrine",
            "website": "vitrine",
            "ecommerce": "ecommerce",
            "booking": "booking",
            "web_app": "web_app",
            "crm": "crm",
        }
        return mapping.get(project_type, "vitrine")


seo_agent = SEOAgent()
