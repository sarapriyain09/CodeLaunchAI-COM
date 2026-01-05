from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.blueprint import Blueprint
from app.services.planner import plan_blueprint

router = APIRouter()


class PlanRequest(BaseModel):
    goal: str = Field(..., min_length=5, description='User request in plain English')
    context: Optional[Dict[str, Any]] = Field(default=None, description='Optional additional hints')


class PlanResponse(BaseModel):
    blueprint: Blueprint
    meta: Dict[str, Any] = Field(default_factory=dict)


@router.post('/plan', response_model=PlanResponse)
async def create_plan(body: PlanRequest) -> PlanResponse:
    try:
        blueprint, debug = await plan_blueprint(body.goal, body.context)
        return PlanResponse(blueprint=blueprint, meta=debug)
    except HTTPException:
        raise
    except Exception as error:  # pragma: no cover - surface failure for MVP
        raise HTTPException(status_code=400, detail=f'Failed to generate blueprint: {error}') from error
