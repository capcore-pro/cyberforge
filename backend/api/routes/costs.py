"""
Coûts API par projet — suivi en mémoire (cost_tracker).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cost_tracker import build_costs_api_response, reset_cost

router = APIRouter(tags=["costs"])


class ArchitectPlanCosts(BaseModel):
    complexity_score: int = Field(ge=1, le=10)
    complexity_label: str
    market_price_min: int = Field(ge=0)
    market_price_max: int = Field(ge=0)
    suggested_price_min: int = Field(ge=0)
    suggested_price_max: int = Field(ge=0)


class ProjectCostsResponse(BaseModel):
    project_id: str
    total_eur: float = Field(ge=0)
    by_service: dict[str, float] = Field(default_factory=dict)
    architect_plan: ArchitectPlanCosts | None = None
    margin_multiplier: int | None = None
    updated_at: str


class ResetCostsResponse(BaseModel):
    status: str = "reset"


@router.get("/projects/{project_id}/costs", response_model=ProjectCostsResponse)
async def get_project_costs(project_id: str) -> ProjectCostsResponse:
    """Résumé des coûts API et tarification ArchitectAI pour un projet."""
    payload: dict[str, Any] = build_costs_api_response(project_id.strip())
    return ProjectCostsResponse(**payload)


@router.delete("/projects/{project_id}/costs", response_model=ResetCostsResponse)
async def delete_project_costs(project_id: str) -> ResetCostsResponse:
    """Remet à zéro le suivi des coûts (et le plan ArchitectAI associé)."""
    reset_cost(project_id.strip())
    return ResetCostsResponse()
