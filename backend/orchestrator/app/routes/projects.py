from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.projects import CreateProjectRequest, DeleteProjectResponse, ListProjectsResponse, Project
from app.services.project_access import get_project_owner_key
from app.services.project_store import create_project, delete_project, get_project, list_projects


router = APIRouter()


@router.get("/projects", response_model=ListProjectsResponse)
def projects_list(request: Request) -> ListProjectsResponse:
    owner_key = get_project_owner_key(request)
    return ListProjectsResponse(projects=list_projects(owner_key=owner_key))


@router.post("/projects", response_model=Project)
def projects_create(request: Request, body: CreateProjectRequest) -> Project:
    owner_key = get_project_owner_key(request)
    try:
        return create_project(owner_key=owner_key, name=body.name, project_id=body.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/projects/{project_id}", response_model=Project)
def projects_get(request: Request, project_id: str) -> Project:
    owner_key = get_project_owner_key(request)
    project = get_project(owner_key=owner_key, project_id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", response_model=DeleteProjectResponse)
def projects_delete(request: Request, project_id: str) -> DeleteProjectResponse:
    owner_key = get_project_owner_key(request)
    removed = delete_project(owner_key=owner_key, project_id=project_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Project not found")
    return DeleteProjectResponse(deleted=True)
