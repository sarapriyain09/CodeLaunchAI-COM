from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class Branding(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=60)
    tagline: Optional[str] = Field(None, max_length=120)
    logo_url: Optional[HttpUrl] = None


class Theme(BaseModel):
    style: Literal['modern', 'minimal', 'playful', 'corporate', 'bold'] = 'modern'
    primary_color: Optional[str] = Field(None, description='Hex color like #2563EB')
    font_family: Optional[str] = Field(None, description='e.g., Inter, Poppins')


class Route(BaseModel):
    path: str = Field(..., description="URL path like '/', '/pricing', '/contact'")
    title: str = Field(..., min_length=1, max_length=60)
    layout: Literal['default', 'dashboard'] = 'default'


class Component(BaseModel):
    name: str = Field(..., description='PascalCase component name, e.g., PricingSection')
    description: str = Field(..., max_length=200)
    used_on_routes: List[str] = Field(default_factory=list, description='List of route paths that use it')


class DataModelField(BaseModel):
    name: str
    type: Literal['string', 'number', 'boolean', 'date', 'json'] = 'string'
    required: bool = True


class DataModel(BaseModel):
    name: str = Field(..., description='PascalCase model name, e.g., Product, User')
    fields: List[DataModelField] = Field(default_factory=list)


class Integration(BaseModel):
    kind: Literal['stripe', 'email', 'auth', 'storage', 'database', 'maps', 'analytics']


class Blueprint(BaseModel):
    schema_version: str = Field('1.0', description='Blueprint schema version')
    app_type: Literal['website', 'webapp', 'ecommerce'] = 'website'

    goal: str = Field(..., description='One sentence goal for the build')
    target_audience: Optional[str] = None

    branding: Branding
    theme: Theme = Theme()

    routes: List[Route] = Field(..., min_items=1)
    components: List[Component] = Field(default_factory=list)

    data_models: List[DataModel] = Field(default_factory=list)
    integrations: List[Integration] = Field(default_factory=list)

    constraints: List[str] = Field(default_factory=list, description="e.g., 'Use Tailwind', 'Mobile-first'")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Checklist describing 'done'")
