"""
Service Knowledge Graph — synchronisation et enrichissement post-génération.
"""

from __future__ import annotations

import logging
from typing import Any

from db.agent_registry_store import get_agent_registry_store
from db.knowledge_graph_store import get_knowledge_graph_store
from db.knowledge_store import get_knowledge_store
from db.prompt_store import get_prompt_store
from db.tool_store import get_tool_store
from db.workflow_store import get_workflow_store

logger = logging.getLogger(__name__)


def _get_agents_for_type(project_type: str) -> list[str]:
    base = ["brief", "design_system", "generator", "supervisor", "deploy"]
    pt = (project_type or "").strip().lower()
    if pt in ("application_web", "crm", "real_app"):
        base += ["database", "auth"]
    elif pt in ("ecommerce", "site_reservation"):
        base += ["database", "payment"]
    elif pt == "extension_navigateur":
        return ["brief", "deploy"]
    return base


class KnowledgeGraphService:
    def __init__(self) -> None:
        self._graph_store = get_knowledge_graph_store()
        self._agent_store = get_agent_registry_store()
        self._workflow_store = get_workflow_store()
        self._tool_store = get_tool_store()
        self._prompt_store = get_prompt_store()
        self._knowledge_store = get_knowledge_store()

    async def sync_from_database(self) -> dict[str, Any]:
        """Construit le graphe initial depuis les tables existantes."""
        nodes = 0
        edges = 0

        agents = await self._agent_store.list_all(enabled=None)
        for agent in agents:
            await self._graph_store.upsert_node(
                entity_type="agent",
                entity_id=str(agent["agent_id"]),
                label=str(agent["name"]),
                properties={
                    "category": agent.get("category"),
                    "model": agent.get("model"),
                    "in_pipeline": agent.get("in_pipeline"),
                },
            )
            nodes += 1

        workflows = await self._workflow_store.list_workflows(status="active")
        for wf in workflows:
            wf_key = str(wf["workflow_id"])
            await self._graph_store.upsert_node(
                entity_type="workflow",
                entity_id=wf_key,
                label=str(wf["name"]),
                properties={"project_types": wf.get("project_types", [])},
            )
            nodes += 1

            steps = await self._workflow_store.get_steps(str(wf["id"]))
            for step in steps:
                agent_id = step.get("agent_id")
                if agent_id:
                    await self._graph_store.upsert_edge(
                        source_type="workflow",
                        source_id=wf_key,
                        target_type="agent",
                        target_id=str(agent_id),
                        relation_type="uses",
                        weight=1.0,
                    )
                    edges += 1
                    tool_id = step.get("tool_id")
                    if tool_id:
                        await self._graph_store.upsert_edge(
                            source_type="agent",
                            source_id=str(agent_id),
                            target_type="tool",
                            target_id=str(tool_id),
                            relation_type="triggers",
                            weight=1.0,
                        )
                        edges += 1

        tools = await self._tool_store.list_tools()
        for tool in tools:
            await self._graph_store.upsert_node(
                entity_type="tool",
                entity_id=str(tool["tool_id"]),
                label=str(tool["name"]),
                properties={"category": tool.get("category")},
            )
            nodes += 1

        prompts = await self._prompt_store.list_all(status="active")
        for prompt in prompts:
            slug = str(prompt["slug"])
            await self._graph_store.upsert_node(
                entity_type="prompt",
                entity_id=slug,
                label=str(prompt["name"]),
                properties={"agent_slug": prompt.get("agent_slug")},
            )
            nodes += 1
            agent_slug = prompt.get("agent_slug")
            if agent_slug:
                await self._graph_store.upsert_edge(
                    source_type="prompt",
                    source_id=slug,
                    target_type="agent",
                    target_id=str(agent_slug),
                    relation_type="benchmarks",
                )
                edges += 1

        docs = await self._knowledge_store.list_documents(limit=200)
        for doc in docs:
            doc_id = str(doc["id"])
            await self._graph_store.upsert_node(
                entity_type="document",
                entity_id=doc_id,
                label=str(doc["title"]),
                properties={"source_type": doc.get("source_type")},
            )
            nodes += 1
            project_id = doc.get("project_id")
            if project_id:
                await self._graph_store.upsert_edge(
                    source_type="document",
                    source_id=doc_id,
                    target_type="project",
                    target_id=str(project_id),
                    relation_type="indexed_for",
                )
                edges += 1

        return {
            "nodes_created": nodes,
            "edges_created": edges,
            "status": "synced",
        }

    async def add_generation_to_graph(
        self,
        brief: dict[str, Any],
        generation_id: str,
        project_id: str | None = None,
    ) -> None:
        """Ajoute les relations projet → agents après une génération réussie."""
        project_type = str(brief.get("project_type") or "")
        client_name = str(brief.get("client_name") or "")

        if project_id:
            await self._graph_store.upsert_node(
                entity_type="project",
                entity_id=str(project_id),
                label=client_name or str(project_id)[:8],
                properties={
                    "project_type": project_type,
                    "generation_id": generation_id,
                },
            )

            for agent_id in _get_agents_for_type(project_type):
                await self._graph_store.upsert_edge(
                    source_type="project",
                    source_id=str(project_id),
                    target_type="agent",
                    target_id=agent_id,
                    relation_type="uses",
                    weight=1.0,
                )


graph_service = KnowledgeGraphService()
