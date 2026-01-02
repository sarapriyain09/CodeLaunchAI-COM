from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Project(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class CreateProjectRequest(BaseModel):
    project_id: str | None = Field(default=None, description="Optional client-provided id")
    name: str | None = Field(default=None, max_length=80)


class ListProjectsResponse(BaseModel):
    projects: list[Project]
