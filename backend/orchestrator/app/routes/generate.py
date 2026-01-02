from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.blueprint import Blueprint
from app.schemas.files import FileItem, GenerateResponse
from app.services.generator import generate_vite_react_project

router = APIRouter()


class GenerateRequest(BaseModel):
    blueprint: Blueprint
    project_name: str = Field('generated-app', min_length=2, max_length=60)
    mode: Optional[str] = Field('vite-react-ts-tailwind', description='Future expansion placeholder')


@router.post('/generate', response_model=GenerateResponse)
async def generate_project(body: GenerateRequest) -> GenerateResponse:
    try:
        files_dict = await generate_vite_react_project(body.blueprint, body.project_name)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f'Failed to generate project: {error}') from error

    files = [FileItem(path=path, content=content) for path, content in sorted(files_dict.items())]
    return GenerateResponse(files=files)