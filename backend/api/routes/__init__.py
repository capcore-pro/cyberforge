"""Routes HTTP — API CyberForge (generate, projects, managed-projects, health)."""

from __future__ import annotations

import importlib
import logging as _log

from fastapi import APIRouter

_startup_log = _log.getLogger(__name__)

_failed_modules: list[str] = []

_ROUTER_ORDER: tuple[str, ...] = (
    "health",
    "agents_status",
    "agent_registry",
    "agent_builder",
    "tool_framework",
    "workflows",
    "supervisor",
    "orchestration",
    "communication",
    "generate",
    "coremind",
    "pipeline_stream",
    "projects",
    "editor",
    "clients",
    "client_review",
    "knowledge",
    "knowledge_graph",
    "pipeline",
    "llm_usage",
    "llm_providers",
    "audit",
    "prompts_library",
    "memory",
    "mobile",
    "mobile_builder",
    "erp_builder",
    "monitoring",
    "notifications",
    "demos",
    "demo_tracking",
    "secrets",
    "settings",
    "subdomains",
    "system",
    "scrape_inspiration",
    "clone_inspiration",
    "managed_vitrines",
    "managed_application_web",
    "managed_ecommerce",
    "managed_site_reservation",
    "managed_extensions",
)


def _import_route_module(name: str):
    _startup_log.info("[IMPORT START] %s", name)
    try:
        module = importlib.import_module(f"api.routes.{name}")
        _startup_log.info("[IMPORT OK] %s", name)
        return module
    except Exception as exc:
        _startup_log.error("[IMPORT FAIL] %s: %s", name, exc, exc_info=True)
        _failed_modules.append(name)
        return None


_startup_log.info("[IMPORT] Starting api.routes imports")

_startup_log.info("[IMPORT] Testing common deps...")
try:
    import supabase

    _startup_log.info("[IMPORT OK] supabase")
except Exception as exc:
    _startup_log.error("[IMPORT FAIL] supabase: %s", exc, exc_info=True)

try:
    import anthropic

    _startup_log.info("[IMPORT OK] anthropic")
except Exception as exc:
    _startup_log.error("[IMPORT FAIL] anthropic: %s", exc, exc_info=True)

try:
    from config import get_settings

    get_settings()
    _startup_log.info("[IMPORT OK] config/settings")
except Exception as exc:
    _startup_log.error("[IMPORT FAIL] config/settings: %s", exc, exc_info=True)

_modules: dict[str, object | None] = {}

agent_builder = _modules["agent_builder"] = _import_route_module("agent_builder")
agent_registry = _modules["agent_registry"] = _import_route_module("agent_registry")
agents_status = _modules["agents_status"] = _import_route_module("agents_status")
audit = _modules["audit"] = _import_route_module("audit")
clone_inspiration = _modules["clone_inspiration"] = _import_route_module("clone_inspiration")
clients = _modules["clients"] = _import_route_module("clients")
client_review = _modules["client_review"] = _import_route_module("client_review")
communication = _modules["communication"] = _import_route_module("communication")
coremind = _modules["coremind"] = _import_route_module("coremind")
demos = _modules["demos"] = _import_route_module("demos")
demo_tracking = _modules["demo_tracking"] = _import_route_module("demo_tracking")
editor = _modules["editor"] = _import_route_module("editor")
erp_builder = _modules["erp_builder"] = _import_route_module("erp_builder")
generate = _modules["generate"] = _import_route_module("generate")
health = _modules["health"] = _import_route_module("health")
knowledge = _modules["knowledge"] = _import_route_module("knowledge")
knowledge_graph = _modules["knowledge_graph"] = _import_route_module("knowledge_graph")
llm_usage = _modules["llm_usage"] = _import_route_module("llm_usage")
llm_providers = _modules["llm_providers"] = _import_route_module("llm_providers")
memory = _modules["memory"] = _import_route_module("memory")
mobile = _modules["mobile"] = _import_route_module("mobile")
mobile_builder = _modules["mobile_builder"] = _import_route_module("mobile_builder")
monitoring = _modules["monitoring"] = _import_route_module("monitoring")
prompts_library = _modules["prompts_library"] = _import_route_module("prompts_library")
managed_application_web = _modules["managed_application_web"] = _import_route_module(
    "managed_application_web"
)
managed_ecommerce = _modules["managed_ecommerce"] = _import_route_module("managed_ecommerce")
managed_extensions = _modules["managed_extensions"] = _import_route_module("managed_extensions")
managed_site_reservation = _modules["managed_site_reservation"] = _import_route_module(
    "managed_site_reservation"
)
managed_vitrines = _modules["managed_vitrines"] = _import_route_module("managed_vitrines")
notifications = _modules["notifications"] = _import_route_module("notifications")
orchestration = _modules["orchestration"] = _import_route_module("orchestration")
pipeline = _modules["pipeline"] = _import_route_module("pipeline")
pipeline_stream = _modules["pipeline_stream"] = _import_route_module("pipeline_stream")
projects = _modules["projects"] = _import_route_module("projects")
scrape_inspiration = _modules["scrape_inspiration"] = _import_route_module("scrape_inspiration")
secrets = _modules["secrets"] = _import_route_module("secrets")
settings = _modules["settings"] = _import_route_module("settings")
subdomains = _modules["subdomains"] = _import_route_module("subdomains")
supervisor = _modules["supervisor"] = _import_route_module("supervisor")
system = _modules["system"] = _import_route_module("system")
tool_framework = _modules["tool_framework"] = _import_route_module("tool_framework")
workflows = _modules["workflows"] = _import_route_module("workflows")

API_ROUTERS: list[tuple[APIRouter, str]] = [
    (module.router, "/api")
    for name in _ROUTER_ORDER
    if (module := _modules.get(name)) is not None
]

_startup_log.info(
    "[IMPORT] Done — loaded=%s failed=%s API_ROUTERS=%s",
    len(_modules) - len(_failed_modules),
    len(_failed_modules),
    len(API_ROUTERS),
)

if _failed_modules:
    _startup_log.error(
        "[IMPORT FAIL] Modules non chargés (%s): %s",
        len(_failed_modules),
        _failed_modules,
    )

_ROUTE_MODULE_NAMES: tuple[str, ...] = tuple(_modules.keys())

__all__ = [
    "API_ROUTERS",
    "FAILED_ROUTE_MODULES",
    *_ROUTE_MODULE_NAMES,
]

FAILED_ROUTE_MODULES = tuple(_failed_modules)
