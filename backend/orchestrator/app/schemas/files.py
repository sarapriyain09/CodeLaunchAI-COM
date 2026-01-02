from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    path: str = Field(..., description='Relative path inside the generated project')
    content: str = Field(..., description='UTF-8 encoded file content')


class GenerateResponse(BaseModel):
    files: List[FileItem]