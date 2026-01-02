from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.projects import CreateProjectRequest, ListProjectsResponse, Project
from app.services.project_store import create_project, get_project, list_projects


router = APIRouter()


@router.get("/projects", response_model=ListProjectsResponse)
def projects_list() -> ListProjectsResponse:
    return ListProjectsResponse(projects=list_projects())


@router.post("/projects", response_model=Project)
def projects_create(body: CreateProjectRequest) -> Project:
    try:
        return create_project(name=body.name, project_id=body.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/projects/{project_id}", response_model=Project)
def projects_get(project_id: str) -> Project:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
