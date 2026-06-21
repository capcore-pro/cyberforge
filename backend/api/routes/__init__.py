"""Routes HTTP — API CyberForge (generate, projects, managed-projects, health)."""

from __future__ import annotations

import importlib
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

_failed_modules: list[str] = []

_ROUTE_MODULE_NAMES: tuple[str, ...] = (
    "agent_builder",
    "agent_registry",
    "agents_status",
    "audit",
    "clone_inspiration",
    "clients",
    "client_review",
    "communication",
    "demos",
    "demo_tracking",
    "editor",
    "erp_builder",
    "generate",
    "health",
    "knowledge",
    "knowledge_graph",
    "llm_usage",
    "llm_providers",
    "memory",
    "mobile",
    "mobile_builder",
    "monitoring",
    "prompts_library",
    "managed_application_web",
    "managed_ecommerce",
    "managed_extensions",
    "managed_site_reservation",
    "managed_vitrines",
    "notifications",
    "orchestration",
    "pipeline",
    "projects",
    "scrape_inspiration",
    "secrets",
    "settings",
    "subdomains",
    "supervisor",
    "system",
    "tool_framework",
    "workflows",
)

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
    try:
        return importlib.import_module(f".{name}", package=__name__)
    except Exception as exc:
        logger.error("[IMPORT FAIL] %s: %s", name, exc)
        _failed_modules.append(name)
        return None


_modules: dict[str, object | None] = {
    name: _import_route_module(name) for name in _ROUTE_MODULE_NAMES
}

agent_builder = _modules["agent_builder"]
agent_registry = _modules["agent_registry"]
agents_status = _modules["agents_status"]
audit = _modules["audit"]
clone_inspiration = _modules["clone_inspiration"]
clients = _modules["clients"]
client_review = _modules["client_review"]
communication = _modules["communication"]
demos = _modules["demos"]
demo_tracking = _modules["demo_tracking"]
editor = _modules["editor"]
erp_builder = _modules["erp_builder"]
generate = _modules["generate"]
health = _modules["health"]
knowledge = _modules["knowledge"]
knowledge_graph = _modules["knowledge_graph"]
llm_usage = _modules["llm_usage"]
llm_providers = _modules["llm_providers"]
memory = _modules["memory"]
mobile = _modules["mobile"]
mobile_builder = _modules["mobile_builder"]
monitoring = _modules["monitoring"]
prompts_library = _modules["prompts_library"]
managed_application_web = _modules["managed_application_web"]
managed_ecommerce = _modules["managed_ecommerce"]
managed_extensions = _modules["managed_extensions"]
managed_site_reservation = _modules["managed_site_reservation"]
managed_vitrines = _modules["managed_vitrines"]
notifications = _modules["notifications"]
orchestration = _modules["orchestration"]
pipeline = _modules["pipeline"]
projects = _modules["projects"]
scrape_inspiration = _modules["scrape_inspiration"]
secrets = _modules["secrets"]
settings = _modules["settings"]
subdomains = _modules["subdomains"]
supervisor = _modules["supervisor"]
system = _modules["system"]
tool_framework = _modules["tool_framework"]
workflows = _modules["workflows"]

API_ROUTERS: list[tuple[APIRouter, str]] = [
    (module.router, "/api")
    for name in _ROUTER_ORDER
    if (module := _modules.get(name)) is not None
]

if _failed_modules:
    logger.error("[IMPORT FAIL] Modules non chargés (%s): %s", len(_failed_modules), _failed_modules)

__all__ = [
    "API_ROUTERS",
    "FAILED_ROUTE_MODULES",
    *_ROUTE_MODULE_NAMES,
]

FAILED_ROUTE_MODULES = tuple(_failed_modules)
