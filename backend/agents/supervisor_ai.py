"""
SupervisorAI — validation binaire des sorties agents (dictateur qualité).
"""

from __future__ import annotations

import re
from typing import Any

import httpx

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_VALID_PROJECT_TYPES = frozenset(
    {
        "vitrine",
        "vitrine_next",
        "ecommerce",
        "site_reservation",
        "application_web",
        "application_desktop",
        "real_app",
        "extension_navigateur",
        "saas_dashboard",
    }
)

_BLOCKED_CLIENT_NAMES = frozenset(
    {
        "votre nom",
        "votre nom client",
        "nom client",
        "client",
        "mon entreprise",
        "notre entreprise",
        "entreprise",
        "demo client",
        "démo client",
    }
)

_GENERIC_SERVICES = frozenset(
    {
        "service",
        "service 1",
        "service 2",
        "service 3",
        "prestation",
        "prestation 1",
    }
)

_GENERIC_PRODUCT_NAMES = frozenset(
    {
        "produit unique",
        "produit standard",
        "commande",
        "abonnement pro",
        "produit",
        "product",
    }
)

_HTML_FORBIDDEN_SNIPPETS = (
    "votre ville",
    "votre nom",
    "à préciser",
    "lorem ipsum",
    "placeholder",
    "nom_client",
    "client_name",
    "tagline",
    "votre, france",
    "votre email",
)

_SCRIPT_STYLE_RE = re.compile(
    r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>",
    re.I | re.DOTALL,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CALENDAR_MARKUP_RE = re.compile(
    r"""(?:id|class)=["'][^"']*(?:calendar|calendrier)[^"']*["']""",
    re.I,
)
_HEBERGEMENT_CARD_RE = re.compile(
    r"""<(?:article|div)\b[^>]*class=["'][^"']*(?:hebergement|hebergement-card|lodging|accommodation)[^"']*["']""",
    re.I,
)
_DATA_HEBERGEMENT_RE = re.compile(r"data-(?:hebergement|accommodation|lodging)-", re.I)


def _has_footer_markup(html: str, low: str) -> bool:
    """Détecte un pied de page explicite ou sémantique (balise, class, id)."""
    if re.search(r"<footer\b", html, re.I):
        return True
    if re.search(r"""class=["'][^"']*\bfooter\b""", html, re.I):
        return True
    if re.search(r"""id=["']footer["']""", html, re.I):
        return True
    if 'class="footer"' in low or "class='footer'" in low:
        return True
    if 'id="footer"' in low or "id='footer'" in low:
        return True
    return False


def _html_closes_document(low: str) -> bool:
    trimmed = low.rstrip()
    return trimmed.endswith("</html>") or trimmed.endswith("</body></html>")


def _is_site_reservation_brief(brief: dict) -> bool:
    b = brief or {}
    for key in ("project_type", "generation_mode"):
        val = str(b.get(key) or "").strip().lower().replace("-", "_")
        if val == "site_reservation":
            return True
    return False


def _has_reservation_form_markup(body: str, low: str) -> bool:
    """Formulaire réservation : mot-clé + au moins un champ input."""
    has_keyword = any(
        token in low for token in ("formulaire", "reservation", "réservation")
    )
    has_input = bool(re.search(r"<input\b", body, re.I))
    return has_keyword and has_input


def _has_page_javascript(body: str, low: str) -> bool:
    """JS présent : bloc <script>, onclick= ou addEventListener."""
    if re.search(r"<script\b", body, re.I):
        return True
    if re.search(r"\bonclick\s*=", body, re.I):
        return True
    return "addeventlistener" in low


def _site_reservation_html_errors(body: str, low: str) -> list[str]:
    """Règles HTML démo camping / hébergements (site_reservation)."""
    errors: list[str] = []

    if not _CALENDAR_MARKUP_RE.search(body):
        errors.append(
            "site_reservation : calendrier manquant (id ou class contenant calendar/calendrier)"
        )

    card_count = len(_HEBERGEMENT_CARD_RE.findall(body))
    data_cards = len(_DATA_HEBERGEMENT_RE.findall(body))
    priced_cards = len(re.findall(r"data-price-per-night\s*=", body, re.I))
    if max(card_count, data_cards, priced_cards) < 2:
        errors.append(
            "site_reservation : moins de 2 cards hébergements "
            "(classes hebergement/lodging ou data-hebergement / data-price-per-night)"
        )

    if not _has_reservation_form_markup(body, low):
        errors.append(
            "site_reservation : formulaire de réservation manquant "
            "(mot formulaire/réservation/reservation + au moins une balise <input>)"
        )

    if not _has_page_javascript(body, low):
        errors.append(
            "site_reservation : JavaScript manquant "
            "(balise <script>, onclick= ou addEventListener)"
        )
    else:
        if not any(k in low for k in ("nuit", "nuits", "night", "montant", "total", "prix")):
            errors.append(
                "site_reservation : JavaScript de calcul prix/nuits manquant "
                "(mots-clés nuit, montant, total ou prix)"
            )
        if not any(
            k in low
            for k in ("calendar", "calendrier", "arriv", "depart", "checkin", "checkout")
        ):
            errors.append(
                "site_reservation : JavaScript calendrier manquant "
                "(sélection dates arrivée/départ)"
            )

    if "confirmer" not in low and "réservation" not in low and "reservation" not in low:
        errors.append(
            "site_reservation : bouton ou libellé « Confirmer la réservation » manquant"
        )

    return errors


def _visible_text_from_html(html: str) -> str:
    """Texte visible uniquement (sans balises, scripts, styles ni attributs)."""
    text = html or ""
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _HTML_COMMENT_RE.sub(" ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _html_correction_instructions(errors: list[str], brief: dict) -> str:
    """Instructions courtes pour GeneratorAI (une ligne par type d'erreur)."""
    client_name = str(brief.get("client_name") or "").strip()
    primary = str(brief.get("couleur_primaire") or "").strip()
    secondary = str(brief.get("couleur_secondaire") or "").strip()
    lines: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        if line not in seen:
            seen.add(line)
            lines.append(line)

    missing_body = any("balise manquante : <body" in e for e in errors)
    missing_html = any("balise manquante : <html" in e for e in errors)
    missing_head = any("balise manquante : <head" in e for e in errors)

    if missing_body or (missing_html and missing_head):
        add(
            "CORRECTION OBLIGATOIRE : Génère un HTML complet avec <html><head><body>"
        )
    elif missing_html:
        add("CORRECTION OBLIGATOIRE : Inclus la balise <html> à la racine du document")
    elif missing_head:
        add(
            "CORRECTION OBLIGATOIRE : Inclus un <head> avec <title> et un bloc <style>"
        )
    elif missing_body:
        add("CORRECTION OBLIGATOIRE : Inclus un <body> avec tout le contenu visible")

    for err in errors:
        if err.startswith("HTML trop court"):
            add(
                "CORRECTION OBLIGATOIRE : Génère un HTML complet (minimum 3000 caractères)"
            )
        elif err.startswith("document HTML incomplet"):
            add(
                "CORRECTION OBLIGATOIRE : Le HTML a été coupé — termine par "
                "</footer></body></html> avec toutes les sections "
                "(pas d'arrêt après le hero)"
            )
        elif err.startswith("balise manquante :"):
            continue
        elif err.startswith("client_name «") and "absent du HTML" in err:
            if client_name:
                add(
                    f"CORRECTION OBLIGATOIRE : Affiche le nom exact « {client_name} » "
                    "dans le corps de la page"
                )
        elif err == "client_name absent du <title>":
            if client_name:
                add(
                    f"CORRECTION OBLIGATOIRE : Mets « {client_name} » dans la balise <title>"
                )
        elif err == "<style> CSS manquant":
            add("CORRECTION OBLIGATOIRE : Ajoute un bloc <style> avec le CSS du site")
        elif err == "nav ou header manquant":
            add("CORRECTION OBLIGATOIRE : Ajoute un <nav> ou un <header>")
        elif err == "section manquante":
            add("CORRECTION OBLIGATOIRE : Ajoute au moins 3 balises <section>")
        elif err == "footer manquant":
            add("CORRECTION OBLIGATOIRE : Ajoute un <footer> avant </body>")
        elif err == "section hero introuvable":
            add(
                "CORRECTION OBLIGATOIRE : Ajoute une section hero plein écran "
                "(min-height 60vh)"
            )
        elif err == "hero display:none détecté":
            add("CORRECTION OBLIGATOIRE : Le hero doit être visible (pas display:none)")
        elif err == "hero sans min-height/height visible":
            add(
                "CORRECTION OBLIGATOIRE : Définis min-height ou height sur le hero "
                "(ex. min-height: 60vh)"
            )
        elif err.startswith("texte interdit détecté :"):
            snippet = err.split("«")[-1].split("»")[0].strip() if "«" in err else ""
            if snippet:
                add(
                    f"CORRECTION OBLIGATOIRE : Supprime le texte « {snippet} » "
                    "du contenu visible"
                )
        elif err.startswith("couleur ") and "absente" in err:
            err_low = err.lower()
            if primary and primary.lower() in err_low:
                add(
                    f"CORRECTION OBLIGATOIRE : Utilise la couleur {primary} "
                    "dans le CSS (--color-primary)"
                )
            if secondary and secondary.lower() in err_low:
                add(
                    f"CORRECTION OBLIGATOIRE : Utilise la couleur {secondary} "
                    "dans le CSS (--color-secondary)"
                )
        elif err == "aucune balise <img>":
            add(
                "CORRECTION OBLIGATOIRE : Ajoute au moins 3 balises "
                "<img class='pexels-inject'>"
            )
        elif err == 'src local http://127.0.0.1 interdit':
            add(
                "CORRECTION OBLIGATOIRE : N'utilise pas src='http://127.0.0.1' "
                "sur les images"
            )
        elif err.startswith("site_reservation :"):
            add(f"CORRECTION SITE RÉSERVATION : {err.removeprefix('site_reservation : ')}")

    if client_name and any("client_name" in e for e in errors):
        if not any(client_name in ln for ln in lines):
            add(
                f"CORRECTION OBLIGATOIRE : Mets « {client_name} » dans <title> et dans <h1>"
            )

    return "\n".join(lines)

_STALE_DEPLOYMENT_NAMES = (
    "reprise simplifiée",
    "reprise simplifiee",
    "demo client",
    "démo client",
    "loi visuelle",
    "cyberforge demo",
    "acme corp",
    "example corp",
    "nom de l'entreprise",
)

_SECTOR_TABLE_HINTS: dict[str, tuple[str, ...]] = {
    "boulangerie": ("products", "orders", "contact"),
    "camping": ("reservations", "services", "contact", "appointments"),
    "commerce": ("products", "orders", "customers", "contact"),
    "restaurant": ("reservations", "menu", "orders", "contact"),
    "ecommerce": ("products", "orders", "customers", "categories"),
    "reservation": ("appointments", "services", "customers", "bookings"),
    "sante": ("appointments", "patients", "services"),
    "beaute": ("appointments", "services", "customers"),
}


def _result(
    valid: bool,
    errors: list[str],
    *,
    corrected_prompt: str = "",
) -> dict[str, Any]:
    return {
        "valid": valid,
        "errors": errors,
        "corrected_prompt": corrected_prompt if not valid else "",
    }


def _is_meaningful_text(value: str, *, min_len: int = 2) -> bool:
    s = (value or "").strip()
    if len(s) < min_len:
        return False
    low = s.lower()
    if low in _BLOCKED_CLIENT_NAMES:
        return False
    return True


def _hex_ok(value: str) -> bool:
    return bool(_HEX_RE.match((value or "").strip()))


def _sector_keywords(sector: str) -> tuple[str, ...]:
    low = (sector or "").strip().lower()
    for key, hints in _SECTOR_TABLE_HINTS.items():
        if key in low:
            return hints
    if "ecommerce" in low or "boutique" in low:
        return _SECTOR_TABLE_HINTS["ecommerce"]
    if "reserv" in low or "rendez" in low:
        return _SECTOR_TABLE_HINTS["reservation"]
    return ("contact", "customers", "services")


class SupervisorAI:
    """Valide les livrables agents ; fournit des prompts de correction pour relance."""

    async def validate_brief(self, brief: dict) -> dict[str, Any]:
        errors: list[str] = []
        b = brief or {}

        client_name = str(b.get("client_name") or "").strip()
        if not _is_meaningful_text(client_name, min_len=3):
            errors.append("client_name absent ou générique")

        project_type = str(b.get("project_type") or "").strip().lower()
        if not project_type or project_type not in _VALID_PROJECT_TYPES:
            errors.append(f"project_type invalide : {project_type or '(vide)'}")

        sector = str(b.get("sector") or "").strip()
        description = str(b.get("description") or "").strip()
        if not _is_meaningful_text(sector, min_len=2):
            errors.append("sector absent")
        elif description and sector.lower() not in description.lower():
            desc_low = description.lower()
            if not any(tok in desc_low for tok in sector.lower().split() if len(tok) > 3):
                errors.append("sector peu cohérent avec la description")

        if len(description) < 50:
            errors.append("description trop courte (< 50 caractères)")

        services = b.get("services")
        if not isinstance(services, list) or not services:
            errors.append("services : liste vide")
        else:
            real = [
                str(s).strip()
                for s in services
                if _is_meaningful_text(str(s), min_len=3)
                and str(s).strip().lower() not in _GENERIC_SERVICES
            ]
            if not real:
                errors.append("services : aucun service réel (libellés génériques)")

        if not _hex_ok(str(b.get("couleur_primaire") or "")):
            errors.append("couleur_primaire : hex invalide (#XXXXXX requis)")
        if not _hex_ok(str(b.get("couleur_secondaire") or "")):
            errors.append("couleur_secondaire : hex invalide (#XXXXXX requis)")

        if not str(b.get("ambiance") or "").strip():
            errors.append("ambiance vide")

        filled_meta = 0
        for key in ("ville", "phone", "email", "font", "mots_cles_seo"):
            val = b.get(key)
            if key == "mots_cles_seo":
                if isinstance(val, list) and any(str(x).strip() for x in val):
                    filled_meta += 1
            elif _is_meaningful_text(str(val or ""), min_len=2):
                filled_meta += 1
        if filled_meta < 3:
            errors.append(
                "moins de 3 champs remplis parmi ville, phone, email, font, mots_cles_seo"
            )

        if errors:
            corrections = (
                "Corrige le brief JSON : "
                + "; ".join(errors)
                + ". Nom client réel, description > 50 caractères, 3+ métadonnées, "
                "services concrets, couleurs #RRGGBB, secteur aligné sur l'activité."
            )
            base = str(b.get("prompt") or description or "")
            corrected_prompt = f"{base}\n\n{corrections}".strip()
            return _result(False, errors, corrected_prompt=corrected_prompt)

        return _result(True, [])

    async def validate_html(self, html: str, brief: dict) -> dict[str, Any]:
        errors: list[str] = []
        body = html or ""
        low = body.lower()
        b = brief or {}
        client_name = str(b.get("client_name") or "").strip()
        name_low = client_name.lower()

        if len(body) < 3000:
            errors.append(f"HTML trop court ({len(body)} car., minimum 3000)")

        if not _html_closes_document(low):
            errors.append("document HTML incomplet : balise </html> manquante")

        for tag in ("<html", "<head", "<body"):
            if tag not in low:
                errors.append(f"balise manquante : {tag}")

        if client_name:
            if name_low not in low:
                errors.append(f"client_name « {client_name} » absent du HTML")
            title_m = re.search(r"<title[^>]*>([^<]*)</title>", body, re.I)
            if title_m and name_low not in (title_m.group(1) or "").lower():
                errors.append(f"client_name absent du <title>")

        if "<style" not in low:
            errors.append("<style> CSS manquant")

        has_nav = bool(re.search(r"<nav\b|<header\b", body, re.I))
        has_section = bool(re.search(r"<section\b", body, re.I))
        has_footer = _has_footer_markup(body, low)
        if not has_nav:
            errors.append("nav ou header manquant")
        if not has_section:
            errors.append("section manquante")
        if not has_footer:
            if _html_closes_document(low) and len(body) > 8000:
                pass
            else:
                errors.append("footer manquant")

        hero_block = re.search(
            r"<(?:section|div|header)[^>]*(?:id|class)=[\"'][^\"']*hero[^\"']*[\"'][^>]*>",
            body,
            re.I,
        )
        if not hero_block and "class=\"hero\"" not in low and "class='hero'" not in low:
            errors.append("section hero introuvable")
        else:
            hero_snippet = body[hero_block.start() : hero_block.start() + 800] if hero_block else ""
            if re.search(r"display\s*:\s*none", hero_snippet, re.I):
                errors.append("hero display:none détecté")
            if hero_snippet and not re.search(
                r"min-height\s*:|height\s*:\s*\d",
                hero_snippet,
                re.I,
            ):
                if not re.search(r"min-height\s*:|height\s*:\s*\d", low[:4000], re.I):
                    errors.append("hero sans min-height/height visible")

        visible_low = _visible_text_from_html(body)
        for snippet in _HTML_FORBIDDEN_SNIPPETS:
            if snippet in visible_low:
                errors.append(f"texte interdit détecté : « {snippet} »")

        primary = str(b.get("couleur_primaire") or "").strip()
        if primary and primary.lower() not in low:
            errors.append(f"couleur {primary} absente du CSS/HTML")

        if not re.search(r"<img\b", body, re.I):
            errors.append("aucune balise <img>")

        if 'src="http://127.0.0.1' in low or "src='http://127.0.0.1" in low:
            errors.append('src local http://127.0.0.1 interdit')

        if _is_site_reservation_brief(b):
            errors.extend(_site_reservation_html_errors(body, low))

        if errors:
            corrected_prompt = _html_correction_instructions(errors, b)
            return _result(False, errors, corrected_prompt=corrected_prompt)

        return _result(True, [])

    async def validate_deployment(self, url: str, client_name: str) -> dict[str, Any]:
        errors: list[str] = []
        target = (url or "").strip()
        name = (client_name or "").strip()
        name_low = name.lower()

        if not target.startswith("http"):
            errors.append("URL de déploiement invalide")
            return _result(False, errors)

        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(target)
        except Exception as exc:
            errors.append(f"GET échoué : {exc}")
            return _result(False, errors)

        if response.status_code != 200:
            errors.append(f"status HTTP {response.status_code} (attendu 200)")

        page = response.text or ""
        page_low = page.lower()

        if name and name_low not in page_low:
            errors.append(f"client_name « {name} » absent de la page déployée")

        for stale in _STALE_DEPLOYMENT_NAMES:
            if stale in page_low and stale not in name_low:
                errors.append(f"ancien contenu détecté : « {stale} »")

        if errors:
            return _result(False, errors)

        return _result(True, [])

    async def validate_database(self, schema: dict, brief: dict) -> dict[str, Any]:
        errors: list[str] = []
        s = schema or {}
        b = brief or {}
        sector = str(b.get("sector") or "").strip().lower()

        tables = s.get("tables")
        if not isinstance(tables, list) or not tables:
            errors.append("tables vide")
        elif len(tables) < 2:
            errors.append(f"tables insuffisantes ({len(tables)}, minimum 2)")

        sql = str(s.get("sql") or "")
        if not sql.strip():
            errors.append("sql vide")
        elif "create table" not in sql.lower():
            errors.append("sql sans CREATE TABLE")

        if isinstance(tables, list) and tables and sector:
            names = [
                str(t.get("name") or "").lower()
                for t in tables
                if isinstance(t, dict)
            ]
            hints = _sector_keywords(sector)
            if not any(any(h in n for h in hints) for n in names if n):
                errors.append(
                    f"tables peu cohérentes avec le secteur « {b.get('sector')} »"
                )

        if errors:
            corrected = (
                "Regénère un schéma Supabase : "
                + "; ".join(errors)
                + f". Minimum 2 tables métier pour secteur {b.get('sector', 'activité')}."
            )
            return _result(False, errors, corrected_prompt=corrected)

        return _result(True, [])

    async def validate_payment(self, payment: dict, brief: dict) -> dict[str, Any]:
        errors: list[str] = []
        p = payment or {}
        b = brief or {}

        payment_type = str(p.get("payment_type") or "").strip().lower()
        if payment_type not in ("one_shot", "subscription", "booking", "none"):
            errors.append(f"payment_type invalide : {payment_type or '(vide)'}")

        if payment_type == "none":
            return _result(True, [])

        stripe = p.get("stripe_config")
        if not isinstance(stripe, dict) or not stripe:
            errors.append("stripe_config vide")

        products = []
        if isinstance(stripe, dict):
            products = stripe.get("products") or []
        if not isinstance(products, list) or not products:
            errors.append("products vide")
        else:
            names: list[str] = []
            for item in products:
                if isinstance(item, dict):
                    names.append(str(item.get("name") or "").strip())
                else:
                    names.append(str(item).strip())
            real = [
                n
                for n in names
                if _is_meaningful_text(n, min_len=3)
                and n.lower() not in _GENERIC_PRODUCT_NAMES
            ]
            if not real:
                errors.append("noms de produits génériques (Produit Unique, etc.)")

            client_low = str(b.get("client_name") or "").lower()
            sector_low = str(b.get("sector") or "").lower()
            if client_low or sector_low:
                coherent = any(
                    client_low[:6] in n.lower()
                    or any(tok in n.lower() for tok in sector_low.split() if len(tok) > 4)
                    for n in real
                )
                if real and not coherent:
                    errors.append("produits peu cohérents avec le brief client")

        prices = stripe.get("prices") if isinstance(stripe, dict) else []
        if not isinstance(prices, list) or not prices:
            errors.append("prices vide")

        if errors:
            corrected = (
                "Regénère payment_config Stripe : "
                + "; ".join(errors)
                + f". Produits nommés selon {b.get('client_name')} / {b.get('sector')}."
            )
            return _result(False, errors, corrected_prompt=corrected)

        return _result(True, [])
