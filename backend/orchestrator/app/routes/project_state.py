from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.schemas.project_state import ProjectState, UpdateProjectStateRequest

router = APIRouter()


@router.get("/projects/{project_id}/state", response_model=ProjectState)
def get_project_state(project_id: str) -> ProjectState:
    if not db_enabled():
        raise HTTPException(status_code=501, detail="Postgres not configured (set DATABASE_URL)")

    with session_scope() as session:
        row = session.get(ProjectRow, project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectState(
            project_id=row.id,
            updated_at=row.updated_at,
            blueprint=row.blueprint or {},
            plan=row.plan or {},
        )


@router.put("/projects/{project_id}/state", response_model=ProjectState)
def put_project_state(project_id: str, body: UpdateProjectStateRequest) -> ProjectState:
    if not db_enabled():
        raise HTTPException(status_code=501, detail="Postgres not configured (set DATABASE_URL)")

    with session_scope() as session:
        row = session.get(ProjectRow, project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        if body.blueprint is not None:
            row.blueprint = body.blueprint
        if body.plan is not None:
            row.plan = body.plan

        session.flush()

        return ProjectState(
            project_id=row.id,
            updated_at=row.updated_at,
            blueprint=row.blueprint or {},
            plan=row.plan or {},
        )
