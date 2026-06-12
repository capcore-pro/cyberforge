"""
DatabaseAI — génère un schéma Supabase/PostgreSQL à partir d'une description projet.

Interface:
    async def run(project_description: str, project_type: str, design_system: dict) -> dict

Retour:
    {
      "tables": [...],
      "sql": "-- SQL complet prêt à exécuter dans Supabase",
      "summary": "Description courte du schéma généré"
    }
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import anthropic

from agents.llm_usage_utils import usage_from_anthropic_response
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env")
)


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 6000


SYSTEM_PROMPT = """Tu es DatabaseAI, expert Supabase/PostgreSQL.
Analyse la description du projet et génère un schéma SQL complet.

Règles obligatoires :
- Chaque table a toujours : id UUID DEFAULT gen_random_uuid() PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT NOW()
- Utiliser UUID pour toutes les clés primaires et étrangères
- Ajouter Row Level Security (RLS) sur toutes les tables
- Policies RLS : lecture publique pour données non sensibles, écriture authentifiée uniquement
- Ajouter des index sur les colonnes fréquemment filtrées (foreign keys, status, email)
- Nommer les tables en snake_case au pluriel
- Ajouter des commentaires SQL sur chaque table

Types de projets → tables typiques :
- vitrine : contact_messages (id, name, email, message, read, created_at)
- ecommerce : products, categories, orders, order_items, customers
- site_reservation : accommodations (hébergements), customers, bookings (séjour), blocked_dates
- application_web : selon description métier (garage → vehicles/repairs/invoices, CRM → leads/contacts/deals)
- application_desktop : même logique que application_web

Retourner UNIQUEMENT un JSON valide sans markdown ni backticks :
{
  "tables": [{"name": "...", "columns": [...], "description": "..."}],
  "sql": "-- SQL complet avec CREATE TABLE, RLS, policies, indexes",
  "summary": "Description courte du schéma"
}

IMPORTANT pour le JSON :
- Dans le champ 'sql', utiliser uniquement des apostrophes simples pour les valeurs SQL (jamais de guillemets doubles à l'intérieur du SQL)
- Ne jamais dépasser 6000 caractères pour le champ 'sql'
- Le JSON doit être parseable par json.loads() sans erreur
- Pas de caractères spéciaux non échappés dans les strings JSON
""".strip()


def _default_schema(project_type: str) -> dict[str, Any]:
    pt = (project_type or "").strip().lower().replace("-", "_")
    if pt == "vitrine":
        tables = [
            {
                "name": "contact_messages",
                "columns": ["name text", "email text", "message text", "read boolean default false"],
                "description": "Messages envoyés via formulaire de contact.",
            }
        ]
    elif pt == "ecommerce":
        tables = [
            {
                "name": "customers",
                "columns": ["name text", "email text", "phone text"],
                "description": "Clients.",
            },
            {
                "name": "categories",
                "columns": ["name text", "slug text"],
                "description": "Catégories produits.",
            },
            {
                "name": "products",
                "columns": [
                    "category_id uuid references public.categories(id)",
                    "name text",
                    "description text",
                    "price_cents integer",
                    "status text",
                ],
                "description": "Catalogue produits.",
            },
            {
                "name": "orders",
                "columns": [
                    "customer_id uuid references public.customers(id)",
                    "status text",
                    "total_cents integer",
                ],
                "description": "Commandes client.",
            },
            {
                "name": "order_items",
                "columns": [
                    "order_id uuid references public.orders(id)",
                    "product_id uuid references public.products(id)",
                    "quantity integer",
                    "unit_price_cents integer",
                ],
                "description": "Lignes de commande.",
            },
        ]
    elif pt == "site_reservation":
        tables = [
            {
                "name": "accommodations",
                "columns": [
                    "name text not null",
                    "type text not null",
                    "capacity integer not null",
                    "price_per_night_cents integer not null",
                    "description text",
                    "image_url text",
                    "status text default 'active'",
                ],
                "description": "Hébergements (mobil-home, chalet, tente, caravane).",
            },
            {
                "name": "customers",
                "columns": [
                    "first_name text",
                    "last_name text",
                    "email text",
                    "phone text",
                ],
                "description": "Clients voyageurs.",
            },
            {
                "name": "bookings",
                "columns": [
                    "accommodation_id uuid references public.accommodations(id)",
                    "customer_id uuid references public.customers(id)",
                    "check_in date not null",
                    "check_out date not null",
                    "nights integer not null",
                    "total_cents integer not null",
                    "status text default 'pending'",
                    "notes text",
                ],
                "description": "Réservations séjour (arrivée, départ, montant).",
            },
            {
                "name": "blocked_dates",
                "columns": [
                    "accommodation_id uuid references public.accommodations(id)",
                    "blocked_date date not null",
                    "reason text",
                ],
                "description": "Dates indisponibles au calendrier.",
            },
        ]
    elif pt == "application_desktop":
        tables = [
            {
                "name": "users",
                "columns": ["email text", "display_name text"],
                "description": "Utilisateurs.",
            },
            {
                "name": "records",
                "columns": ["user_id uuid references public.users(id)", "title text", "data jsonb", "status text"],
                "description": "Enregistrements génériques.",
            },
        ]
    else:
        # application_web + générique
        tables = [
            {
                "name": "users",
                "columns": ["email text", "display_name text"],
                "description": "Utilisateurs.",
            },
            {
                "name": "items",
                "columns": ["user_id uuid references public.users(id)", "title text", "description text", "status text"],
                "description": "Items génériques (à adapter).",
            },
        ]

    sql = _build_sql_from_tables(tables)
    return {
        "tables": tables,
        "sql": sql,
        "summary": f"Schéma par défaut généré pour {pt or 'application_web'} ({len(tables)} table(s)).",
    }


def _build_sql_from_tables(tables: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("-- DatabaseAI — schéma SQL Supabase")
    lines.append("create extension if not exists pgcrypto;")
    lines.append("")

    for t in tables:
        name = str(t.get("name") or "").strip()
        desc = str(t.get("description") or "").strip() or f"Table {name}."
        cols = t.get("columns") or []
        if not name:
            continue
        if not isinstance(cols, list):
            cols = []

        lines.append(f"-- {desc}")
        lines.append(f"create table if not exists public.{name} (")
        lines.append("  id uuid primary key default gen_random_uuid(),")
        lines.append("  created_at timestamptz not null default now(),")
        for raw in cols:
            col = str(raw).strip().rstrip(",")
            if not col:
                continue
            lines.append(f"  {col},")
        # retire la virgule finale sur la dernière colonne si nécessaire
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]
        lines.append(");")
        lines.append(f"comment on table public.{name} is {json.dumps(desc, ensure_ascii=False)};")
        lines.append("")

        # RLS + policies génériques
        lines.append(f"alter table public.{name} enable row level security;")
        lines.append(f"drop policy if exists \"public_read\" on public.{name};")
        lines.append(f"create policy \"public_read\" on public.{name} for select using (true);")
        lines.append(f"drop policy if exists \"auth_write\" on public.{name};")
        lines.append(
            f"create policy \"auth_write\" on public.{name} "
            "for all to authenticated using (true) with check (true);"
        )
        lines.append("")

        # Index de base: email/status + foreign keys
        col_text = " ".join(str(c) for c in cols)
        if "email" in col_text:
            lines.append(f"create index if not exists {name}_email_idx on public.{name} (email);")
        if "status" in col_text:
            lines.append(f"create index if not exists {name}_status_idx on public.{name} (status);")
        fk_cols = []
        for c in cols:
            m = re.match(r"^\s*([a-zA-Z0-9_]+)\s+uuid\b", str(c))
            if m and m.group(1).endswith("_id"):
                fk_cols.append(m.group(1))
        for fk in fk_cols:
            lines.append(f"create index if not exists {name}_{fk}_idx on public.{name} ({fk});")
        if fk_cols or "email" in col_text or "status" in col_text:
            lines.append("")

    return "\n".join(lines).strip() + "\n"


async def _call_claude(system_prompt: str, user_prompt: str):
    def _do_call():
        return client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

    return await asyncio.to_thread(_do_call)


async def run(project_description: str, project_type: str, design_system: dict) -> dict:
    """
    Analyse la description et retourne {tables, sql, summary}.
    En cas d'erreur (LLM ou parsing), retourne un schéma minimal par défaut.
    """
    import json as json_module

    desc = (project_description or "").strip()
    pt = (project_type or "").strip()
    ds = design_system if isinstance(design_system, dict) else {}

    reservation_hint = ""
    if pt.replace("-", "_") == "site_reservation":
        reservation_hint = (
            "\n\n## Schéma attendu (site_reservation / hébergements)\n"
            "Tables obligatoires : accommodations, customers, bookings, blocked_dates.\n"
            "accommodations : type (mobil_home, chalet, tente, caravane), capacity, "
            "price_per_night_cents.\n"
            "bookings : check_in, check_out, nights, total_cents, accommodation_id, customer_id.\n"
            "blocked_dates : accommodation_id, blocked_date pour indisponibilités calendrier.\n"
        )

    user_prompt = (
        "## Description du projet\n"
        f"{desc}\n\n"
        "## Type de projet\n"
        f"{pt}\n\n"
        "## Design system (contexte)\n"
        f"{json_module.dumps(ds, ensure_ascii=False)[:6000]}"
        f"{reservation_hint}"
    ).strip()

    try:
        import re

        response = await _call_claude(SYSTEM_PROMPT, user_prompt)

        raw_text = response.content[0].text
        print(
            f"[DatabaseAI DEBUG] Réponse brute (500 premiers chars):\n{raw_text[:500]}"
        )

        # Étape 1 : nettoyer les fences markdown
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        # Étape 2 : trouver le début et la fin du JSON principal
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Aucun JSON trouvé")
        json_str = cleaned[start : end + 1]

        # Étape 3 : parser
        parsed = json_module.loads(json_str)

        # Étape 4 : vérifier les clés
        if not all(k in parsed for k in ["tables", "sql", "summary"]):
            raise ValueError("JSON incomplet — clés manquantes")

        tables = parsed.get("tables")
        sql = parsed.get("sql")
        summary = parsed.get("summary")
        if not isinstance(tables, list) or not isinstance(sql, str) or not isinstance(summary, str):
            raise ValueError("JSON incomplet (tables/sql/summary).")
        result = {"tables": tables, "sql": sql, "summary": summary}
        usage = usage_from_anthropic_response(response, MODEL)
        if usage:
            result["usage"] = usage
        return result
    except Exception as _ex:
        print(f"[DatabaseAI PARSE ERROR] {_ex}"); return _default_schema(pt)

