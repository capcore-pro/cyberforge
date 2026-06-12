"""
AuthAI — génère un système d'authentification Supabase complet selon le type de projet.

Interface:
    async def run(project_description: str, project_type: str, database_schema: dict) -> dict

Retour:
    {
      "auth_type": "public" | "single_user" | "multi_user" | "agency",
      "sql": "-- SQL complet ou vide si public",
      "roles": [],
      "summary": ""
    }
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

import anthropic  # noqa: E402

from agents.llm_usage_utils import usage_from_anthropic_response  # noqa: E402

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 4096

AuthType = Literal["public", "single_user", "multi_user", "agency"]


def detect_auth_type(project_description: str, project_type: str) -> AuthType:
    pt = (project_type or "").strip().lower()
    if pt in ("vitrine_next", "extension_navigateur"):
        return "public"

    text = (project_description or "").strip().lower()
    if any(k in text for k in ("agence", "multi-tenant", "organisations", "clients entreprises")):
        return "agency"
    if any(
        k in text
        for k in (
            "equipe",
            "équipe",
            "employe",
            "employé",
            "collaborateur",
            "staff",
            "plusieurs utilisateurs",
        )
    ):
        return "multi_user"
    return "single_user"


SYSTEM_PROMPT = """
Tu es AuthAI, expert Supabase Auth et Row Level Security PostgreSQL.
Génère le SQL d'authentification complet selon le auth_type fourni.

Pour single_user :
- Pas de table users custom
- RLS policies sur toutes les tables : auth.uid() IS NOT NULL pour écriture
- Lecture publique sur les données non sensibles

Pour multi_user :
- Table user_profiles (id UUID REFERENCES auth.users PRIMARY KEY, role TEXT CHECK (role IN ('admin','manager','employee')), full_name TEXT, avatar_url TEXT, created_at TIMESTAMPTZ DEFAULT NOW())
- Fonction SQL : get_user_role() RETURNS TEXT
- RLS policies par rôle sur chaque table du database_schema
- Admin : accès total
- Manager : lecture/écriture sauf suppression
- Employee : lecture seule

Pour agency :
- Table organizations (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, name TEXT, owner_id UUID REFERENCES auth.users, plan TEXT DEFAULT 'free', created_at TIMESTAMPTZ DEFAULT NOW())
- Table user_profiles (id UUID REFERENCES auth.users PRIMARY KEY, org_id UUID REFERENCES organizations, role TEXT CHECK (role IN ('super_admin','org_admin','org_member')), full_name TEXT, created_at TIMESTAMPTZ DEFAULT NOW())
- RLS multi-tenant : chaque org ne voit que ses propres données
- Fonction get_user_org_id() RETURNS UUID

Retourner UNIQUEMENT un JSON valide sans markdown :
{
  "auth_type": "...",
  "sql": "-- SQL complet avec apostrophes simples dans les strings SQL",
  "roles": ["role1", "role2"],
  "summary": "Description courte"
}
""".strip()


def _tables_from_schema(database_schema: dict) -> list[str]:
    tables = database_schema.get("tables") if isinstance(database_schema, dict) else None
    if not isinstance(tables, list):
        return []
    names: list[str] = []
    for t in tables:
        if isinstance(t, dict) and t.get("name"):
            names.append(str(t["name"]).strip())
    return [n for n in names if n]


def _fallback_sql_single_user(tables: list[str]) -> str:
    lines: list[str] = []
    lines.append("-- AuthAI fallback — single_user")
    for table in tables:
        lines.append(f"alter table public.{table} enable row level security;")
        lines.append(f"drop policy if exists 'public_read' on public.{table};")
        lines.append(f"create policy 'public_read' on public.{table} for select using (true);")
        lines.append(f"drop policy if exists 'auth_write' on public.{table};")
        lines.append(
            f"create policy 'auth_write' on public.{table} "
            "for all to authenticated using (auth.uid() is not null) "
            "with check (auth.uid() is not null);"
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _fallback_sql_multi_user(tables: list[str]) -> str:
    lines: list[str] = []
    lines.append("-- AuthAI fallback — multi_user")
    lines.append("create extension if not exists pgcrypto;")
    lines.append(
        "create table if not exists public.user_profiles ("
        "id uuid references auth.users primary key, "
        "role text not null check (role in ('admin','manager','employee')), "
        "full_name text, "
        "avatar_url text, "
        "created_at timestamptz default now()"
        ");"
    )
    lines.append("alter table public.user_profiles enable row level security;")
    lines.append("drop policy if exists 'profiles_self_read' on public.user_profiles;")
    lines.append(
        "create policy 'profiles_self_read' on public.user_profiles for select "
        "to authenticated using (auth.uid() = id);"
    )
    lines.append("drop policy if exists 'profiles_self_write' on public.user_profiles;")
    lines.append(
        "create policy 'profiles_self_write' on public.user_profiles for update "
        "to authenticated using (auth.uid() = id) with check (auth.uid() = id);"
    )
    lines.append("")
    lines.append(
        "create or replace function public.get_user_role() returns text "
        "language sql stable as $$ "
        "select role from public.user_profiles where id = auth.uid() $$;"
    )
    lines.append("")

    for table in tables:
        lines.append(f"alter table public.{table} enable row level security;")
        lines.append(f"drop policy if exists 'public_read' on public.{table};")
        lines.append(f"create policy 'public_read' on public.{table} for select using (true);")
        lines.append(f"drop policy if exists 'admin_all' on public.{table};")
        lines.append(
            f"create policy 'admin_all' on public.{table} "
            "for all to authenticated using (public.get_user_role() = 'admin') "
            "with check (public.get_user_role() = 'admin');"
        )
        lines.append(f"drop policy if exists 'manager_rw' on public.{table};")
        lines.append(
            f"create policy 'manager_rw' on public.{table} "
            "for insert to authenticated with check (public.get_user_role() = 'manager');"
        )
        lines.append(
            f"create policy 'manager_rw_update' on public.{table} "
            "for update to authenticated using (public.get_user_role() = 'manager') "
            "with check (public.get_user_role() = 'manager');"
        )
        lines.append(f"drop policy if exists 'employee_read' on public.{table};")
        lines.append(
            f"create policy 'employee_read' on public.{table} "
            "for select to authenticated using (public.get_user_role() = 'employee');"
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _fallback_sql_agency(tables: list[str]) -> str:
    lines: list[str] = []
    lines.append("-- AuthAI fallback — agency")
    lines.append("create extension if not exists pgcrypto;")
    lines.append(
        "create table if not exists public.organizations ("
        "id uuid primary key default gen_random_uuid(), "
        "name text not null, "
        "owner_id uuid references auth.users, "
        "plan text default 'free', "
        "created_at timestamptz default now()"
        ");"
    )
    lines.append(
        "create table if not exists public.user_profiles ("
        "id uuid references auth.users primary key, "
        "org_id uuid references public.organizations(id), "
        "role text not null check (role in ('super_admin','org_admin','org_member')), "
        "full_name text, "
        "created_at timestamptz default now()"
        ");"
    )
    lines.append("alter table public.organizations enable row level security;")
    lines.append("alter table public.user_profiles enable row level security;")
    lines.append("")
    lines.append(
        "create or replace function public.get_user_org_id() returns uuid "
        "language sql stable as $$ "
        "select org_id from public.user_profiles where id = auth.uid() $$;"
    )
    lines.append("")

    for table in tables:
        lines.append(f"alter table public.{table} enable row level security;")
        # NOTE: fallback multi-tenant suppose la présence d'une colonne org_id.
        lines.append(f"drop policy if exists 'tenant_read' on public.{table};")
        lines.append(
            f"create policy 'tenant_read' on public.{table} "
            "for select to authenticated using (org_id = public.get_user_org_id());"
        )
        lines.append(f"drop policy if exists 'tenant_write' on public.{table};")
        lines.append(
            f"create policy 'tenant_write' on public.{table} "
            "for all to authenticated using (org_id = public.get_user_org_id()) "
            "with check (org_id = public.get_user_org_id());"
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


class _FallbackContent:
    def __init__(self, text: str) -> None:
        self.text = text


class _FallbackResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FallbackContent(text)]


async def _call_claude(system_prompt: str, user_prompt: str):
    def _do_call():
        return client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

    try:
        return await asyncio.to_thread(_do_call)
    except anthropic.APIError as exc:
        import logging

        logging.getLogger(__name__).warning("[AuthAI] Anthropic failed: %s", exc)
        from llm.base_provider import LLMRequest
        from llm.router import llm_router

        llm_response = await llm_router.route(
            LLMRequest(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                model=None,
                max_tokens=MAX_TOKENS,
            ),
            task_type="analysis",
        )
        return _FallbackResponse(llm_response.content)


async def run(project_description: str, project_type: str, database_schema: dict) -> dict:
    import json as json_module
    import re

    detected = detect_auth_type(project_description, project_type)
    if detected == "public":
        return {
            "auth_type": "public",
            "sql": "",
            "roles": [],
            "summary": "Projet public — authentification non requise.",
        }

    schema_tables = _tables_from_schema(database_schema)
    user_prompt = (
        "## auth_type\n"
        f"{detected}\n\n"
        "## project_type\n"
        f"{(project_type or '').strip()}\n\n"
        "## project_description\n"
        f"{(project_description or '').strip()}\n\n"
        "## database_schema (JSON)\n"
        f"{json_module.dumps(database_schema or {}, ensure_ascii=False)[:8000]}"
    ).strip()

    try:
        response = await _call_claude(SYSTEM_PROMPT, user_prompt)
        raw_text = response.content[0].text

        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Aucun JSON trouvé")
        json_str = cleaned[start : end + 1]
        parsed = json_module.loads(json_str)

        if not all(k in parsed for k in ["auth_type", "sql", "roles", "summary"]):
            raise ValueError("JSON incomplet — clés manquantes")

        result = {
            "auth_type": parsed.get("auth_type") or detected,
            "sql": parsed.get("sql") or "",
            "roles": parsed.get("roles") or [],
            "summary": parsed.get("summary") or "",
        }
        usage = usage_from_anthropic_response(response, MODEL)
        if usage:
            result["usage"] = usage
        return result
    except Exception:
        if detected == "single_user":
            return {
                "auth_type": "single_user",
                "sql": _fallback_sql_single_user(schema_tables),
                "roles": [],
                "summary": "Fallback single_user — policies RLS génériques.",
            }
        if detected == "multi_user":
            return {
                "auth_type": "multi_user",
                "sql": _fallback_sql_multi_user(schema_tables),
                "roles": ["admin", "manager", "employee"],
                "summary": "Fallback multi_user — profils + rôles + policies génériques.",
            }
        return {
            "auth_type": "agency",
            "sql": _fallback_sql_agency(schema_tables),
            "roles": ["super_admin", "org_admin", "org_member"],
            "summary": "Fallback agency — organizations + multi-tenant policies génériques.",
        }

