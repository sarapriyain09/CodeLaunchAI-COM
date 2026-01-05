from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from app.schemas.project_state import ProjectState, UpdateProjectStateRequest
from app.services.project_state_store import get_project_state_payload, put_project_state_payload
from app.services.project_store import get_project

router = APIRouter()


@router.get("/projects/{project_id}/state", response_model=ProjectState)
def get_project_state(project_id: str) -> ProjectState:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    payload = get_project_state_payload(project_id)
    if payload is None:
        return ProjectState(
            project_id=project_id,
            updated_at=datetime.now(timezone.utc),
            blueprint={},
            plan={},
        )

    updated_at, blueprint, plan = payload
    return ProjectState(project_id=project_id, updated_at=updated_at, blueprint=blueprint, plan=plan)


@router.put("/projects/{project_id}/state", response_model=ProjectState)
def put_project_state(project_id: str, body: UpdateProjectStateRequest) -> ProjectState:
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        updated_at, blueprint, plan = put_project_state_payload(
            project_id, blueprint=body.blueprint, plan=body.plan
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ProjectState(project_id=project_id, updated_at=updated_at, blueprint=blueprint, plan=plan)
