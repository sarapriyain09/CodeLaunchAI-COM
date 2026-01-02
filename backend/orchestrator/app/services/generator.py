from __future__ import annotations

import re
from typing import Dict, List

from app.schemas.blueprint import Blueprint, Route
from app.services.llm_client import LLMConnectionError, call_gpt_chat
from app.services.templates_vite_react import vite_react_ts_tailwind_base_files

GEN_SYSTEM_PROMPT = """You generate ONLY React + TypeScript component code for a single page.
No markdown, fences, or commentary.
Use Tailwind CSS utility classes.
Do not import arbitrary libraries; rely on React core and Tailwind.
Keep code clean, production friendly, and accessible.

Images:
- If you need images, ALWAYS use remote placeholder images (no local files).
- Use deterministic URLs from https://picsum.photos so the page has real images immediately.
    Example: https://picsum.photos/seed/hero-home/1200/700
- Always set meaningful alt text.
"""


def _to_component_name(route: Route) -> str:
    if route.path == '/':
        return 'Home'
    slug = route.path.strip('/') or 'Page'
    # Sanitize for safe filenames across OSes.
    # Examples:
    #  - /products/:id -> ProductsId
    #  - /blog/[slug] -> BlogSlug
    #  - /user/{id}   -> UserId
    slug = re.sub(r'[^a-zA-Z0-9]+', ' ', slug)
    parts = [p for p in slug.split() if p]
    name = ''.join(word[:1].upper() + word[1:] for word in parts)
    if not name:
        name = 'Page'
    # TS identifiers can't start with a digit.
    if name[0].isdigit():
        name = f'Page{name}'
    return name


def _page_file_path(component_name: str) -> str:
    return f'src/pages/{component_name}.tsx'


def _nav_label(route: Route) -> str:
    if route.path == '/':
        return 'Home'
    return route.title or route.path.strip('/').title() or 'Page'


def _insert_marker(text: str, marker: str, insertion: str) -> str:
    return text.replace(marker, insertion + '\n        ' + marker)


async def _generate_page_component(blueprint: Blueprint, route: Route, component_name: str) -> str:
    prompt = f"""Create a React + TypeScript page component.
Route path: {route.path}
Route title: {route.title}
App goal: {blueprint.goal}
Brand: {blueprint.branding.product_name}
Theme: {blueprint.theme.style}

Content requirements:
- Include 2-4 meaningful sections and a CTA if appropriate.
- Use at least 1-3 images where it makes sense (hero image, product cards, gallery, etc.).
- Use picsum.photos images with deterministic seeds that relate to the route:
    - hero image seed: hero-{route.path.strip('/').replace('/', '-') or 'home'}
    - card images can use: card-{route.path.strip('/').replace('/', '-') or 'home'}-1, -2, -3
    - Example: https://picsum.photos/seed/hero-home/1200/700
- Always include alt text.

Return ONLY: export default function {component_name}() {{ ... }}
"""

    try:
        response = await call_gpt_chat(
            [
                {'role': 'system', 'content': GEN_SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
            timeout_s=60.0,
        )
    except LLMConnectionError:
        response = {}

    text = response.get('reply') or response.get('content')
    if not isinstance(text, str) or 'export default function' not in text:
        text = f"""export default function {component_name}() {{\n  return (\n    <div className=\"space-y-4\">\n      <h1 className=\"text-3xl font-semibold\">{route.title}</h1>\n      <p className=\"text-gray-600\">Content coming soon.</p>\n    </div>\n  );\n}}\n"""

    return text.strip() + '\n'


async def generate_vite_react_project(blueprint: Blueprint, project_name: str = 'generated-app') -> Dict[str, str]:
    files = vite_react_ts_tailwind_base_files(project_name)

    files['src/components/Layout.tsx'] = files['src/components/Layout.tsx'].replace(
        'Generated App', blueprint.branding.product_name
    )

    # Defensive fix: earlier template versions had an invalid template-string expression
    # like `${{linkBase}}` which fails TypeScript parsing. Ensure it's corrected.
    layout = files.get('src/components/Layout.tsx', '')
    bad = 'className={({ isActive }) => `${{linkBase}} ${{isActive ? linkActive : ""}}`}'
    good = 'className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}'
    if bad in layout:
        files['src/components/Layout.tsx'] = layout.replace(bad, good)

    routes: List[Route] = list(blueprint.routes)
    if not any(route.path == '/' for route in routes):
        routes.insert(0, Route(path='/', title='Home', layout='default'))

    route_imports: List[str] = []
    route_entries: List[str] = []
    nav_entries: List[str] = []

    for route in routes:
        component_name = _to_component_name(route)
        page_code = await _generate_page_component(blueprint, route, component_name)
        files[_page_file_path(component_name)] = page_code

        if route.path != '/':
            route_imports.append(f'import {component_name} from "./pages/{component_name}";')
            route_entries.append(f'<Route path="{route.path}" element={{<{component_name} />}} />')
            nav_entries.append(
                f"""<NavLink
              to="{route.path}"
              className={{({{ isActive }}) => `${{linkBase}} ${{isActive ? linkActive : ""}}`}}
            >
              {_nav_label(route)}
            </NavLink>"""
            )

    app_tsx = files['src/App.tsx']
    if route_imports:
        app_tsx = app_tsx.replace(
            '// Pages inserted by generator:\nimport Home from "./pages/Home";',
            '// Pages inserted by generator:\nimport Home from "./pages/Home";\n' + '\n'.join(route_imports),
        )
    if route_entries:
        app_tsx = _insert_marker(app_tsx, '{/* __ROUTES__ */}', '\n        ' + '\n        '.join(route_entries))
    files['src/App.tsx'] = app_tsx

    layout_tsx = files['src/components/Layout.tsx']
    if nav_entries:
        layout_tsx = layout_tsx.replace(
            '{/* __NAV__ */}',
            '\n            ' + '\n            '.join(nav_entries) + '\n            {/* __NAV__ */}',
        )
    files['src/components/Layout.tsx'] = layout_tsx

    return files