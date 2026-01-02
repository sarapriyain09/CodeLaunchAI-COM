from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    project_id: str
    updated_at: datetime
    blueprint: dict = Field(default_factory=dict)
    plan: dict = Field(default_factory=dict)


class UpdateProjectStateRequest(BaseModel):
    blueprint: dict | None = None
    plan: dict | None = None
