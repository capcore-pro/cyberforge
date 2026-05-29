"""
NewsletterAgent — emails personnalisés CapCore via DeepSeek V3.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import Settings, get_settings
from cost_tracker import maybe_track_cost, usage_from_openai_payload
from db.managed_projects_store import ManagedProjectRow, get_managed_projects_store
from db.supabase_store import get_supabase_store
from newsletter_db import (
    SequenceTrigger,
    add_email,
    create_sequence,
    get_contact,
    get_contact_by_email,
    update_contact,
)
from security.llm_secrets import (
    LLM_KEYS_UNAVAILABLE_MSG,
    get_effective_llm_key,
    get_effective_llm_key_for_http,
)
from tools.codegen_service import _parse_json_response, _utf8_json_body

logger = logging.getLogger(__name__)

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"

_PERSONALITY_TONES = frozenset(
    {"chaleureux", "professionnel", "décontracté", "sobre"}
)

_SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "boulangerie": ("boulanger", "boulangerie", "pain", "viennoiserie", "fournil"),
    "médical": ("médecin", "medical", "clinique", "santé", "dentiste", "cabinet"),
    "ecommerce": ("ecommerce", "e-commerce", "boutique", "shop", "panier", "stripe"),
    "coiffure": ("coiffure", "coiffeur", "salon", "barbier"),
    "restaurant": ("restaurant", "resto", "menu", "réservation table"),
    "immobilier": ("immobilier", "agence immo", "appartement", "maison"),
    "artisan": ("artisan", "plombier", "électricien", "menuisier"),
}

_BANNED_PHRASES = (
    "j'espère que vous allez bien",
    "j espere que vous allez bien",
    "n'hésitez pas à nous contacter",
    "n hesitez pas a nous contacter",
    "n'hésitez pas à me contacter",
    "cordialement,",
    "dans l'attente de votre retour",
    "je reste à votre disposition",
)

_ANALYZE_SYSTEM = """Tu es l'agent newsletter CapCore (Mathias Gibiard, micro-entrepreneur digital).
Analyse le client livré et réponds UNIQUEMENT en JSON valide (pas de markdown) avec exactement :
{
  "personality_tone": "chaleureux" | "professionnel" | "décontracté" | "sobre",
  "key_values": ["valeur1", "valeur2", "valeur3"],
  "communication_style": "2-3 phrases sur comment s'adresser à eux",
  "ice_breaker": "une phrase d'accroche ultra personnalisée pour CE client"
}
Règles : français, concret, basé sur le secteur et le projet — jamais générique."""

_WELCOME_SYSTEM = """Tu rédiges la séquence de bienvenue CapCore (3 emails) pour un client qui vient de recevoir son site.
Réponds UNIQUEMENT en JSON valide :
{
  "emails": [
    {"type": "welcome_j0", "subject": "...", "html_body": "..."},
    {"type": "welcome_j1", "subject": "...", "html_body": "..."},
    {"type": "welcome_j3", "subject": "...", "html_body": "..."}
  ]
}

Contraintes globales :
- Français, ton humain adapté au profil client (voir personality)
- JAMAIS : "J'espère que vous allez bien", "N'hésitez pas à nous contacter", formules corporate vides
- Chaque email doit mentionner des détails précis (nom, secteur, type de site, URL si fournie)
- html_body : fragment HTML (pas de <html>/<head>), balises simples <p> <ul> <li> <strong> <a>, styles inline légers si besoin
- Signature exacte en fin de chaque email :
  <p style="margin-top:24px;color:#64748b;font-size:14px;">Mat — CapCore<br><a href="mailto:capcore.pro@gmail.com">capcore.pro@gmail.com</a></p>

J0 "Votre site est en ligne" : annonce livraison + URL + 1 conseil secteur personnalisé
J+1 "Comment bien démarrer" : 3 actions concrètes selon le type de projet (vitrine / ecommerce / réservation / app)
J+3 "Un retour ?" : court, humain, demande feedback + modification gratuite si besoin + relation long terme"""

_NEWSLETTER_SYSTEM = """Tu rédiges une newsletter CapCore pour Mat (micro-entrepreneur, CyberForge).
Réponds UNIQUEMENT en JSON : {"subject": "...", "html_body": "..."}
Ton : humain, direct, comme un ami pro — pas corporate.
Français. HTML fragment compatible email (pas de <html>).
Interdit : formules génériques d'excuse ou de politesse creuse.
Signature Mat — CapCore en bas."""


class NewsletterAgentError(Exception):
    """Erreur métier NewsletterAgent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_sector(text: str) -> str | None:
    lower = text.lower()
    for sector, keywords in _SECTOR_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return sector
    return None


def _deepseek_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(get_effective_llm_key("DEEPSEEK_API_KEY", s))


async def _call_deepseek(
    *,
    system: str,
    user: str,
    settings: Settings | None = None,
    project_id: str | None = None,
    temperature: float = 0.35,
    max_tokens: int | None = None,
) -> str:
    s = settings or get_settings()
    api_key = get_effective_llm_key("DEEPSEEK_API_KEY", s)
    if not api_key:
        raise NewsletterAgentError(LLM_KEYS_UNAVAILABLE_MSG)

    model = s.coremind_deepseek_model
    cap = max_tokens or s.coremind_max_output_tokens
    body, headers = _utf8_json_body(
        {
            "model": model,
            "temperature": temperature,
            "max_tokens": cap,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    )
    timeout = httpx.Timeout(s.coremind_llm_timeout_seconds, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            DEEPSEEK_CHAT_URL,
            headers={
                "Authorization": f"Bearer {get_effective_llm_key_for_http('DEEPSEEK_API_KEY', s) or api_key}",
                **headers,
            },
            content=body,
        )

    if response.status_code >= 400:
        snippet = response.content.decode("utf-8", errors="replace")[:400]
        raise NewsletterAgentError(f"DeepSeek HTTP {response.status_code}: {snippet}")

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if not str(content).strip():
        raise NewsletterAgentError("Réponse DeepSeek vide.")

    if project_id:
        maybe_track_cost(
            project_id,
            "deepseek_v3",
            usage_from_openai_payload(payload),
        )

    return str(content)


async def _call_deepseek_json(
    *,
    system: str,
    user: str,
    settings: Settings | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    text = await _call_deepseek(
        system=system,
        user=user,
        settings=settings,
        project_id=project_id,
    )
    return _parse_json_response(text)


def _managed_context(row: ManagedProjectRow, auth_email: str | None) -> dict[str, Any]:
    prompt = row.prompt_original or row.prompt_last or ""
    title = (row.title or row.slug or "Projet").strip()
    sector = _detect_sector(f"{prompt} {title}")
    site_url = (row.url_production or row.url_preview or "").strip() or None
    return {
        "source": "managed",
        "project_id": row.id,
        "client_name": title,
        "company": title,
        "project_type": row.type,
        "sector": sector,
        "site_url": site_url,
        "prompt": prompt,
        "client_email": auth_email,
        "status": row.status,
    }


async def _fetch_project_context(project_id: str) -> dict[str, Any]:
    """Charge le contexte livraison (managed_projects prioritaire, puis Supabase)."""
    pid = project_id.strip()
    managed_store = get_managed_projects_store()
    if managed_store.is_configured():
        try:
            row = await managed_store.get_project(pid)
            if row is not None:
                auth = await managed_store.get_project_auth(pid)
                email = auth.client_email.strip() if auth and auth.client_email else None
                return _managed_context(row, email)
        except Exception:
            logger.exception("Lecture managed_project %s", pid)

    store = get_supabase_store()
    if store.is_configured():
        try:
            detail = await store.get_project(pid)
            if detail is not None:
                p = detail.project
                prompt = p.prompt or ""
                title = p.title or "Projet"
                sector = _detect_sector(f"{prompt} {title} {p.summary or ''}")
                return {
                    "source": "supabase",
                    "project_id": p.id,
                    "client_name": title,
                    "company": title,
                    "project_type": p.project_type,
                    "sector": sector,
                    "site_url": None,
                    "prompt": prompt,
                    "client_email": None,
                    "summary": p.summary,
                }
        except Exception:
            logger.exception("Lecture projet Supabase %s", pid)

    raise NewsletterAgentError(f"Projet introuvable ou stores non configurés : {pid}")


def _normalize_personality(data: dict[str, Any]) -> dict[str, Any]:
    tone = str(data.get("personality_tone", "professionnel")).strip().lower()
    if tone not in _PERSONALITY_TONES:
        tone = "professionnel"
    values = data.get("key_values") or []
    if not isinstance(values, list):
        values = [str(values)]
    key_values = [str(v).strip() for v in values if str(v).strip()][:3]
    while len(key_values) < 3:
        key_values.append("qualité")
    return {
        "personality_tone": tone,
        "key_values": key_values[:3],
        "communication_style": str(data.get("communication_style", "")).strip(),
        "ice_breaker": str(data.get("ice_breaker", "")).strip(),
    }


def _load_personality(contact: dict[str, Any]) -> dict[str, Any] | None:
    raw = (contact.get("personality_notes") or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "personality_tone" in data:
            return _normalize_personality(data)
    except json.JSONDecodeError:
        pass
    return None


def _sanitize_html(html: str) -> str:
    text = html.strip()
    lower = text.lower()
    for phrase in _BANNED_PHRASES:
        if phrase in lower:
            text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return text.strip()


def wrap_email_html(body_fragment: str, *, preview_line: str | None = None) -> str:
    """Enveloppe un fragment HTML pour Brevo."""
    preheader = preview_line or ""
    preheader_block = (
        f'<div style="display:none;max-height:0;overflow:hidden;">{preheader}</div>'
        if preheader
        else ""
    )
    return (
        f'{preheader_block}'
        '<div style="font-family:Segoe UI,Helvetica,Arial,sans-serif;'
        'font-size:16px;line-height:1.55;color:#0f172a;max-width:600px;margin:0 auto;">'
        f"{body_fragment}"
        "</div>"
    )


def _ensure_contact_for_context(
    ctx: dict[str, Any],
    *,
    email: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    import newsletter_db as db

    pid = str(ctx.get("project_id") or "")
    existing = None
    if email:
        existing = get_contact_by_email(email)
    if existing is None and pid:
        for row in db.list_contacts(limit=500):
            if row.get("project_id") == pid:
                existing = row
                break

    client_email = (email or ctx.get("client_email") or "").strip().lower()
    if not client_email:
        slug = re.sub(r"[^a-z0-9]+", "-", (ctx.get("company") or "client").lower()).strip("-")
        client_email = f"{slug or 'client'}+{pid[:8]}@placeholder.capcore.local"

    client_name = (name or ctx.get("client_name") or ctx.get("company") or "Client").strip()

    if existing:
        return existing

    return db.add_contact(
        email=client_email,
        name=client_name,
        company=ctx.get("company"),
        sector=ctx.get("sector"),
        project_id=pid or None,
        project_type=str(ctx.get("project_type") or ""),
    )


async def analyze_contact(project_id: str) -> dict[str, Any]:
    """
    Analyse un projet livré via DeepSeek V3 et persiste le profil dans personality_notes.
    """
    ctx = await _fetch_project_context(project_id)
    user_msg = (
        f"Client / entreprise : {ctx.get('client_name')} / {ctx.get('company')}\n"
        f"Type de projet : {ctx.get('project_type')}\n"
        f"Secteur détecté : {ctx.get('sector') or 'non précisé'}\n"
        f"URL du site : {ctx.get('site_url') or 'non disponible'}\n"
        f"Prompt original :\n{(ctx.get('prompt') or '')[:3000]}\n"
    )
    if ctx.get("summary"):
        user_msg += f"\nRésumé projet : {ctx['summary']}\n"

    raw = await _call_deepseek_json(
        system=_ANALYZE_SYSTEM,
        user=user_msg,
        project_id=project_id,
    )
    personality = _normalize_personality(raw)

    contact = _ensure_contact_for_context(ctx)
    notes_payload = {**personality, "analyzed_at": _utc_now(), "project_context": {
        k: ctx[k] for k in ("project_type", "sector", "site_url", "company") if ctx.get(k)
    }}
    updated = update_contact(
        str(contact["id"]),
        personality_notes=json.dumps(notes_payload, ensure_ascii=False),
        sector=ctx.get("sector") or contact.get("sector"),
        project_type=str(ctx.get("project_type") or ""),
        company=ctx.get("company"),
    )
    if updated is None:
        raise NewsletterAgentError("Mise à jour du contact impossible.")

    return {
        "contact_id": updated["id"],
        "project_id": project_id,
        **personality,
    }


def _project_type_hints(project_type: str) -> str:
    pt = (project_type or "").lower()
    if "ecommerce" in pt:
        return "e-commerce : produits, panier, paiement, fiches produit"
    if "reservation" in pt:
        return "réservation : créneaux, confirmations, rappels clients"
    if "application" in pt or "saas" in pt:
        return "application web : onboarding, parcours utilisateur, support"
    if "vitrine" in pt or "site" in pt or "landing" in pt:
        return "site vitrine : visibilité locale, SEO, prise de contact"
    return "site web professionnel"


_DEFAULT_SCHEDULE_HOURS = {"welcome_j0": 0, "welcome_j1": 24, "welcome_j3": 72}


async def generate_welcome_sequence(
    contact_id: str,
    *,
    trigger: str = "project_delivered",
    sequence_id: str | None = None,
    schedule_offsets_hours: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Génère les 3 emails de bienvenue et les enregistre en base (scheduled)."""
    contact = get_contact(contact_id)
    if contact is None:
        raise NewsletterAgentError(f"Contact inconnu : {contact_id}")

    personality = _load_personality(contact)
    project_id = contact.get("project_id")
    ctx: dict[str, Any] = {}
    if project_id:
        try:
            ctx = await _fetch_project_context(str(project_id))
        except NewsletterAgentError:
            logger.warning("Contexte projet absent pour %s", project_id)
    if personality is None and project_id:
        personality = await analyze_contact(str(project_id))
        contact = get_contact(contact_id) or contact
        personality = _load_personality(contact) or personality

    profile = personality or {
        "personality_tone": "professionnel",
        "key_values": ["qualité", "proximité", "réactivité"],
        "communication_style": "Direct et bienveillant.",
        "ice_breaker": f"Félicitations pour {contact.get('company') or 'votre projet'} !",
    }

    site_url = ctx.get("site_url") or ""
    user_msg = json.dumps(
        {
            "client": {
                "name": contact.get("name"),
                "company": contact.get("company"),
                "sector": contact.get("sector"),
                "project_type": contact.get("project_type") or ctx.get("project_type"),
                "site_url": site_url,
            },
            "personality": profile,
            "project_type_hints": _project_type_hints(
                str(contact.get("project_type") or ctx.get("project_type") or "")
            ),
        },
        ensure_ascii=False,
        indent=2,
    )

    raw = await _call_deepseek_json(
        system=_WELCOME_SYSTEM,
        user=user_msg,
        project_id=str(project_id) if project_id else None,
    )
    emails_raw = raw.get("emails") or []
    if not isinstance(emails_raw, list) or len(emails_raw) < 3:
        raise NewsletterAgentError("Réponse DeepSeek invalide pour la séquence de bienvenue.")

    trig = trigger.strip().lower()
    if trig not in ("project_delivered", "manual", "web_form"):
        trig = "project_delivered"
    if sequence_id:
        seq_id = sequence_id.strip()
    else:
        seq_row = create_sequence(
            contact_id,
            trig,  # type: ignore[arg-type]
            status="in_progress",
        )
        seq_id = str(seq_row["id"])

    hours_map = schedule_offsets_hours or _DEFAULT_SCHEDULE_HOURS
    base_time = datetime.now(timezone.utc)
    stored: list[dict[str, Any]] = []

    for item in emails_raw:
        kind = str(item.get("type", "")).strip().lower()
        if kind not in hours_map:
            continue
        subject = str(item.get("subject", "")).strip()
        body = _sanitize_html(str(item.get("html_body", "")).strip())
        if not subject or not body:
            continue
        scheduled = base_time + timedelta(hours=int(hours_map[kind]))
        html = wrap_email_html(body, preview_line=subject[:120])
        row = add_email(
            type=kind,  # type: ignore[arg-type]
            subject=subject,
            html_content=html,
            sequence_id=seq_id,
            contact_id=contact_id,
            status="scheduled",
            scheduled_at=scheduled.isoformat(),
        )
        stored.append(row)

    if len(stored) < 3:
        raise NewsletterAgentError("Séquence incomplète après génération.")

    return stored


async def generate_newsletter(theme: str, context: str) -> dict[str, Any]:
    """Génère un email newsletter CapCore à partir d'un thème et d'un contexte libre."""
    theme_clean = theme.strip()
    if not theme_clean:
        raise NewsletterAgentError("theme est requis.")

    user_msg = (
        f"Thème demandé par Mat : {theme_clean}\n\n"
        f"Contexte additionnel :\n{context.strip() or '(aucun)'}\n"
    )
    raw = await _call_deepseek_json(system=_NEWSLETTER_SYSTEM, user=user_msg)
    subject = str(raw.get("subject", "")).strip()
    body = _sanitize_html(str(raw.get("html_body", "")).strip())
    if not subject or not body:
        raise NewsletterAgentError("Newsletter générée incomplète.")

    html = wrap_email_html(body, preview_line=subject[:120])
    return add_email(
        type="newsletter",
        subject=subject,
        html_content=html,
        status="draft",
    )
