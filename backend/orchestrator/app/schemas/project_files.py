from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.schemas.files import FileItem


class ProjectFiles(BaseModel):
    project_id: str
    updated_at: datetime
    files: List[FileItem] = Field(default_factory=list)


class UpdateProjectFilesRequest(BaseModel):
    files: List[FileItem] = Field(default_factory=list)
