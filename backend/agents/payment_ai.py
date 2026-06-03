"""
PaymentAI — génère la configuration Stripe complète pour un projet client.

Interface:
    async def run(project_description: str, project_type: str, database_schema: dict) -> dict

Retour:
    {
      "payment_type": "none" | "one_shot" | "subscription" | "booking",
      "stripe_config": { ... },
      "sql": "-- tables Stripe complémentaires",
      "frontend_code": "-- JS Stripe Checkout intégrable",
      "summary": "..."
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Literal

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

import anthropic  # noqa: E402

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 8000

_PARSE_ERROR_PAYLOAD: dict[str, Any] = {
    "payment_type": "none",
    "stripe_config": {},
    "sql": "",
    "frontend_code": "",
    "summary": "PaymentAI parse error - skipped",
}

PaymentType = Literal["none", "one_shot", "subscription", "booking"]


def detect_payment_type(project_description: str, project_type: str) -> PaymentType:
    pt = (project_type or "").strip().lower()
    if pt in ("vitrine_next", "extension_navigateur", "application_desktop"):
        return "none"

    text = (project_description or "").strip().lower()
    if any(k in text for k in ("reservation", "réservation", "rendez-vous", "créneau", "appointment")):
        return "booking"
    if any(k in text for k in ("abonnement", "mensuel", "subscription", "recurring", "saas")):
        return "subscription"
    return "one_shot"


SYSTEM_PROMPT = """
Tu es PaymentAI, expert Stripe et intégration paiement web.
Génère la configuration Stripe complète selon le payment_type fourni.

Pour one_shot (e-commerce) :
- stripe_config : products[], prices[], checkout_session_params
- SQL : orders avec payment_intent_id, payment_status
- frontend_code : JS Stripe Checkout avec fetch /create-checkout-session
- Webhook handler pour payment_intent.succeeded

Pour subscription (SaaS) :
- stripe_config : products[], prices[] avec recurring monthly/yearly, trial_period_days: 14
- SQL : subscriptions (id, user_id, stripe_subscription_id, plan, status, current_period_end)
- frontend_code : JS abonnement avec gestion upgrade/downgrade
- Webhook handlers : customer.subscription.created/updated/deleted

Pour booking (réservation) :
- stripe_config : products[] par service, prices[] par durée
- SQL : payments (id, appointment_id, amount, stripe_payment_intent_id, status)
- frontend_code : JS paiement à la réservation avec confirmation
- Webhook handler pour payment_intent.succeeded → confirmer RDV

Règles :
- Utiliser toujours la clé Stripe du CLIENT (jamais celle de Mat/CapCore)
- Variable : STRIPE_SECRET_KEY (à injecter par le client)
- Mode test par défaut (test_mode: true)
- Commentaires explicatifs en français

Retourner UNIQUEMENT un JSON valide sans markdown :
{
  "payment_type": "...",
  "stripe_config": { "products": [], "prices": [], "webhooks": [] },
  "sql": "-- SQL complémentaire",
  "frontend_code": "// JS Stripe intégrable",
  "summary": "..."
}
""".strip()


async def _call_claude(system_prompt: str, user_prompt: str):
    def _do_call():
        return client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

    return await asyncio.to_thread(_do_call)


def _fallback_payload(payment_type: PaymentType) -> dict[str, Any]:
    if payment_type == "none":
        return {
            "payment_type": "none",
            "stripe_config": {"test_mode": True, "products": [], "prices": [], "webhooks": []},
            "sql": "",
            "frontend_code": "",
            "summary": "Paiement non requis pour ce type de projet.",
        }
    if payment_type == "subscription":
        return {
            "payment_type": "subscription",
            "stripe_config": {
                "test_mode": True,
                "products": [{"name": "Abonnement Pro", "metadata": {"plan": "pro"}}],
                "prices": [
                    {"product": "Abonnement Pro", "currency": "eur", "unit_amount": 2900, "recurring": {"interval": "month"}, "trial_period_days": 14},
                    {"product": "Abonnement Pro", "currency": "eur", "unit_amount": 29000, "recurring": {"interval": "year"}, "trial_period_days": 14},
                ],
                "webhooks": ["customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"],
                "env": ["STRIPE_SECRET_KEY"],
            },
            "sql": "-- SQL fallback subscription\n"
            "create table if not exists public.subscriptions (\n"
            "  id uuid primary key default gen_random_uuid(),\n"
            "  created_at timestamptz not null default now(),\n"
            "  user_id uuid,\n"
            "  stripe_subscription_id text,\n"
            "  plan text,\n"
            "  status text,\n"
            "  current_period_end timestamptz\n"
            ");\n"
            "alter table public.subscriptions enable row level security;\n",
            "frontend_code": "// Fallback: créer une session Stripe Billing côté backend via STRIPE_SECRET_KEY\n",
            "summary": "Fallback subscription — config Stripe minimale + table subscriptions.",
        }
    if payment_type == "booking":
        return {
            "payment_type": "booking",
            "stripe_config": {
                "test_mode": True,
                "products": [{"name": "Réservation", "metadata": {"type": "booking"}}],
                "prices": [{"product": "Réservation", "currency": "eur", "unit_amount": 5000}],
                "webhooks": ["payment_intent.succeeded"],
                "env": ["STRIPE_SECRET_KEY"],
            },
            "sql": "-- SQL fallback booking\n"
            "create table if not exists public.payments (\n"
            "  id uuid primary key default gen_random_uuid(),\n"
            "  created_at timestamptz not null default now(),\n"
            "  appointment_id uuid,\n"
            "  amount integer,\n"
            "  stripe_payment_intent_id text,\n"
            "  status text\n"
            ");\n"
            "alter table public.payments enable row level security;\n",
            "frontend_code": "// Fallback: paiement à la réservation via Stripe Checkout (backend requis)\n",
            "summary": "Fallback booking — config Stripe minimale + table payments.",
        }
    return {
        "payment_type": "one_shot",
        "stripe_config": {
            "test_mode": True,
            "products": [{"name": "Commande", "metadata": {"type": "one_shot"}}],
            "prices": [{"product": "Commande", "currency": "eur", "unit_amount": 1990}],
            "checkout_session_params": {"mode": "payment"},
            "webhooks": ["payment_intent.succeeded"],
            "env": ["STRIPE_SECRET_KEY"],
        },
        "sql": "-- SQL fallback one_shot\n"
        "alter table public.orders add column if not exists payment_intent_id text;\n"
        "alter table public.orders add column if not exists payment_status text;\n",
        "frontend_code": "// Fallback: créer une session Checkout via POST /create-checkout-session\n",
        "summary": "Fallback one_shot — config Stripe minimale + colonnes orders.",
    }


async def run(project_description: str, project_type: str, database_schema: dict) -> dict:
    detected = detect_payment_type(project_description, project_type)
    if detected == "none":
        return _fallback_payload("none")

    user_prompt = (
        "## payment_type\n"
        f"{detected}\n\n"
        "## project_type\n"
        f"{(project_type or '').strip()}\n\n"
        "## project_description\n"
        f"{(project_description or '').strip()}\n\n"
        "## database_schema (JSON)\n"
        f"{json.dumps(database_schema or {}, ensure_ascii=False)[:8000]}"
    ).strip()

    try:
        response = await _call_claude(SYSTEM_PROMPT, user_prompt)
        raw_text = response.content[0].text
        print(
            f"[PaymentAI DEBUG] Réponse brute (300 premiers chars):\n{raw_text[:300]}"
        )

        cleaned = raw_text.strip()
        # Nettoyage fences markdown sans regex (évite extraction regex JSON)
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:]) if len(lines) > 1 else ""
        if cleaned.rstrip().endswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[:-1]) if len(lines) > 1 else ""
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Aucun JSON trouvé")
        json_str = cleaned[start : end + 1]
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[PaymentAI] JSON invalide ou tronqué (max_tokens ?) — paiement ignoré: %s",
                exc,
            )
            return dict(_PARSE_ERROR_PAYLOAD)
        if not isinstance(parsed, dict):
            raise ValueError("JSON racine invalide")
        if not all(k in parsed for k in ["payment_type", "stripe_config", "sql", "frontend_code", "summary"]):
            raise ValueError("JSON incomplet — clés manquantes")

        return {
            "payment_type": str(parsed.get("payment_type") or detected),
            "stripe_config": parsed.get("stripe_config") if isinstance(parsed.get("stripe_config"), dict) else {},
            "sql": str(parsed.get("sql") or ""),
            "frontend_code": str(parsed.get("frontend_code") or ""),
            "summary": str(parsed.get("summary") or ""),
        }
    except Exception as exc:
        logger.warning("[PaymentAI] échec génération — repli fallback: %s", exc)
        return _fallback_payload(detected)

