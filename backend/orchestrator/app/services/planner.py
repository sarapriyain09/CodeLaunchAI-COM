from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from app.schemas.blueprint import Blueprint, Branding, Component, DataModel, DataModelField, Integration, Route, Theme
from app.services.llm_client import LLMConnectionError, call_gpt_chat

PLANNER_SYSTEM_PROMPT = """You are a senior product designer and full-stack architect.\nYou must output ONLY valid JSON matching the Blueprint schema.\nNo markdown. No code fences. No commentary.\n\nRules:\n- Output must be a single JSON object.\n- Use concise, user-friendly titles.\n- Prefer 3–6 routes max for MVP.\n- Components must be reusable and named in PascalCase.\n- If ecommerce: include Product + Order models and 'stripe' integration.\n- Acceptance criteria must be specific and testable.\n"""


def _normalize_blueprint_payload(payload: Any) -> Any:
    """Best-effort normalization of LLM JSON into our strict Blueprint schema.

    The planner prompt asks for strict output, but LLMs often return "near-miss" shapes
    (e.g., data_models[].fields as an object map instead of a list). We convert common
    cases so Blueprint.model_validate succeeds.
    """

    if not isinstance(payload, dict):
        return payload

    obj = dict(payload)

    # branding: must include product_name
    branding = obj.get('branding')
    if isinstance(branding, str):
        obj['branding'] = {'product_name': branding.strip()[:60] or 'CodeLaunchAI Project'}
    elif isinstance(branding, dict):
        b = dict(branding)
        # Common alternatives: name/title/company/brand
        product_name = b.get('product_name')
        if not isinstance(product_name, str) or not product_name.strip():
            for key in ('name', 'title', 'company', 'brand', 'product', 'app_name'):
                v = b.get(key)
                if isinstance(v, str) and v.strip():
                    product_name = v
                    break
        if not isinstance(product_name, str) or not product_name.strip():
            # If the LLM mistakenly placed styling info inside branding, still provide a name.
            product_name = 'CodeLaunchAI Project'
        out_branding: dict[str, Any] = {
            'product_name': product_name.strip()[:60],
            'tagline': b.get('tagline') if isinstance(b.get('tagline'), str) else None,
            'logo_url': b.get('logo_url') if isinstance(b.get('logo_url'), str) else None,
        }
        obj['branding'] = out_branding

    # theme: style must be one of the allowed literals
    theme = obj.get('theme')
    allowed_styles = {'modern', 'minimal', 'playful', 'corporate', 'bold'}
    if isinstance(theme, str):
        theme = {'style': theme}
    if isinstance(theme, dict):
        t = dict(theme)
        style = t.get('style')
        if isinstance(style, str):
            s = style.strip().lower()
            if s not in allowed_styles:
                # Map descriptive phrases to our enum.
                if any(k in s for k in ['minimal', 'clean', 'simple', 'sleek']):
                    s = 'minimal'
                elif any(k in s for k in ['fun', 'playful', 'whimsical', 'cute']):
                    s = 'playful'
                elif any(k in s for k in ['corporate', 'enterprise', 'professional', 'business']):
                    s = 'corporate'
                elif any(k in s for k in ['bold', 'vibrant', 'loud', 'high-contrast']):
                    s = 'bold'
                else:
                    # Cozy/rustic/etc. doesn't exist in our enum; default to modern.
                    s = 'modern'
            t['style'] = s
        elif style is None:
            t['style'] = 'modern'
        obj['theme'] = t

    # constraints: should be List[str]
    constraints = obj.get('constraints')
    if isinstance(constraints, dict):
        obj['constraints'] = [str(k) for k, v in constraints.items() if v]
    elif isinstance(constraints, list):
        normalized_constraints: list[str] = []
        for item in constraints:
            if isinstance(item, str):
                normalized_constraints.append(item)
            elif isinstance(item, dict):
                normalized_constraints.extend([str(k) for k, v in item.items() if v])
            else:
                normalized_constraints.append(str(item))
        obj['constraints'] = normalized_constraints

    # integrations: should be List[{kind: ...}]
    integrations = obj.get('integrations')
    if isinstance(integrations, list):
        normalized_integrations: list[dict[str, Any]] = []
        for item in integrations:
            if isinstance(item, dict):
                if 'kind' in item and isinstance(item.get('kind'), str):
                    normalized_integrations.append({'kind': item['kind']})
                    continue
                # Common alternative: {name: "Stripe", ...}
                name = item.get('name')
                if isinstance(name, str):
                    lname = name.strip().lower()
                    if 'stripe' in lname:
                        normalized_integrations.append({'kind': 'stripe'})
                        continue
                    if 'email' in lname:
                        normalized_integrations.append({'kind': 'email'})
                        continue
                    if 'auth' in lname or 'login' in lname:
                        normalized_integrations.append({'kind': 'auth'})
                        continue
                    if 'storage' in lname:
                        normalized_integrations.append({'kind': 'storage'})
                        continue
                    if 'database' in lname or 'db' in lname:
                        normalized_integrations.append({'kind': 'database'})
                        continue
                    if 'maps' in lname:
                        normalized_integrations.append({'kind': 'maps'})
                        continue
                    if 'analytics' in lname:
                        normalized_integrations.append({'kind': 'analytics'})
                        continue
            elif isinstance(item, str):
                lname = item.strip().lower()
                if lname in {'stripe', 'email', 'auth', 'storage', 'database', 'maps', 'analytics'}:
                    normalized_integrations.append({'kind': lname})
                    continue
                if 'stripe' in lname:
                    normalized_integrations.append({'kind': 'stripe'})
                    continue
        obj['integrations'] = normalized_integrations

    # data_models: fields should be List[{name,type,required}]
    data_models = obj.get('data_models')
    if isinstance(data_models, list):
        normalized_models: list[dict[str, Any]] = []
        for model in data_models:
            if not isinstance(model, dict):
                continue

            model_out: dict[str, Any] = dict(model)
            fields = model_out.get('fields')
            if isinstance(fields, dict):
                # Example: {"id": "string", "price": "number"}
                model_out['fields'] = [
                    {'name': str(fname), 'type': str(ftype).lower(), 'required': True}
                    for fname, ftype in fields.items()
                ]
            elif isinstance(fields, list):
                fixed_fields: list[dict[str, Any]] = []
                for f in fields:
                    if isinstance(f, dict):
                        # Accept {"name": "price", "type": "number", "required": true}
                        if 'name' in f:
                            fixed_fields.append(
                                {
                                    'name': str(f.get('name')),
                                    'type': str(f.get('type', 'string')).lower(),
                                    'required': bool(f.get('required', True)),
                                }
                            )
                        else:
                            # Accept {"price": "number"} as a single-entry dict
                            if len(f) == 1:
                                (k, v) = next(iter(f.items()))
                                fixed_fields.append({'name': str(k), 'type': str(v).lower(), 'required': True})
                    elif isinstance(f, str):
                        # Accept a bare field name string
                        fixed_fields.append({'name': f, 'type': 'string', 'required': True})
                model_out['fields'] = fixed_fields

            normalized_models.append(model_out)
        obj['data_models'] = normalized_models

    return obj


def _extract_text(reply_payload: Dict[str, Any]) -> str:
    if isinstance(reply_payload.get('reply'), str):
        return reply_payload['reply']
    if isinstance(reply_payload.get('content'), str):
        return reply_payload['content']
    return json.dumps(reply_payload)


def _build_user_prompt(goal: str, context: Dict[str, Any] | None) -> str:
    context_block = ''
    if context:
        context_block = '\n\nExtra context:\n' + json.dumps(context, ensure_ascii=False)

    return (
        "Create a Blueprint JSON for this request:\n"
        f"{goal}{context_block}\n\n"
        "Output ONLY JSON with fields: schema_version, app_type, goal, target_audience, "
        "branding, theme, routes, components, data_models, integrations, constraints, acceptance_criteria\n\n"
        "Schema notes (important):\n"
        "- data_models must be a list; each item has fields: name (PascalCase), fields (list of {name,type,required})\n"
        "- integrations must be a list of {kind} where kind is one of: stripe,email,auth,storage,database,maps,analytics\n"
        "- constraints must be a list of strings"
    )


def _fallback_blueprint(goal: str, context: Dict[str, Any] | None) -> Blueprint:
    text = (goal or '').lower()
    is_ecommerce = any(word in text for word in ['ecommerce', 'e-commerce', 'shop', 'store', 'checkout', 'cart'])
    wants_pricing = any(word in text for word in ['pricing', 'plans', 'subscription', 'subscribe'])
    wants_blog = 'blog' in text

    product_name = 'CodeLaunchAI Project'
    if context:
        branding = context.get('branding')
        if isinstance(branding, dict):
            maybe_name = branding.get('product_name')
            if isinstance(maybe_name, str) and maybe_name.strip():
                product_name = maybe_name.strip()[:60]

    routes: List[Route] = [Route(path='/', title='Home', layout='default')]
    if is_ecommerce:
        routes += [
            Route(path='/products', title='Products', layout='default'),
            Route(path='/product', title='Product Detail', layout='default'),
        ]
    if wants_pricing:
        routes.append(Route(path='/pricing', title='Pricing', layout='default'))
    if wants_blog:
        routes.append(Route(path='/blog', title='Blog', layout='default'))
    routes += [
        Route(path='/about', title='About', layout='default'),
        Route(path='/contact', title='Contact', layout='default'),
    ]

    # Keep MVP routes to a sane number
    routes = routes[:6]

    components: List[Component] = [
        Component(name='HeroSection', description='Top hero with headline, value prop, and CTA', used_on_routes=['/']),
        Component(name='FeaturesGrid', description='Grid of key features/benefits', used_on_routes=['/']),
        Component(name='CTASection', description='Primary call-to-action section', used_on_routes=['/']),
        Component(name='ContactSection', description='Contact form / contact details', used_on_routes=['/contact']),
    ]

    data_models: List[DataModel] = []
    integrations: List[Integration] = []
    if is_ecommerce:
        data_models = [
            DataModel(
                name='Product',
                fields=[
                    DataModelField(name='name', type='string', required=True),
                    DataModelField(name='price', type='number', required=True),
                    DataModelField(name='description', type='string', required=False),
                    DataModelField(name='imageUrl', type='string', required=False),
                ],
            ),
            DataModel(
                name='Order',
                fields=[
                    DataModelField(name='email', type='string', required=True),
                    DataModelField(name='items', type='json', required=True),
                    DataModelField(name='total', type='number', required=True),
                    DataModelField(name='createdAt', type='date', required=True),
                ],
            ),
        ]
        integrations = [Integration(kind='stripe')]

    return Blueprint(
        schema_version='1.0',
        app_type='ecommerce' if is_ecommerce else 'website',
        goal=goal,
        target_audience=None,
        branding=Branding(product_name=product_name, tagline=None, logo_url=None),
        theme=Theme(style='modern'),
        routes=routes,
        components=components,
        data_models=data_models,
        integrations=integrations,
        constraints=['Use Tailwind', 'Mobile-first'],
        acceptance_criteria=[
            'Home page renders with a hero, features, and CTA',
            'Navigation links work for all routes',
            'Preview build completes without errors',
        ],
    )


async def plan_blueprint(goal: str, context: Dict[str, Any] | None = None) -> Tuple[Blueprint, Dict[str, Any]]:
    user_prompt = _build_user_prompt(goal, context)

    messages: List[Dict[str, Any]] = [
        {'role': 'system', 'content': PLANNER_SYSTEM_PROMPT},
        {'role': 'user', 'content': user_prompt},
    ]

    try:
        first_reply = await call_gpt_chat(messages)
    except LLMConnectionError as exc:
        blueprint = _fallback_blueprint(goal, context)
        return blueprint, {
            'attempts': 0,
            'offline': True,
            'reason': str(exc)[:500],
        }
    first_text = _extract_text(first_reply)

    try:
        blueprint_obj = json.loads(first_text)
        blueprint_obj = _normalize_blueprint_payload(blueprint_obj)
        blueprint = Blueprint.model_validate(blueprint_obj)
        return blueprint, {'attempts': 1, 'raw': first_text}
    except (json.JSONDecodeError, ValidationError) as error:
        fixer_prompt = (
            'Your previous output was invalid JSON or did not match the schema.\n'
            'Fix it and output ONLY valid JSON, nothing else.\n'
            f"Error summary: {str(error)[:500]}\n"
            'Previous output:\n'
            f'{first_text}'
        )
        second_messages = [
            {'role': 'system', 'content': PLANNER_SYSTEM_PROMPT},
            {'role': 'user', 'content': fixer_prompt},
        ]
        try:
            second_reply = await call_gpt_chat(second_messages)
        except LLMConnectionError as exc:
            blueprint = _fallback_blueprint(goal, context)
            return blueprint, {
                'attempts': 1,
                'offline': True,
                'reason': str(exc)[:500],
            }
        second_text = _extract_text(second_reply)
        blueprint_obj = json.loads(second_text)
        blueprint_obj = _normalize_blueprint_payload(blueprint_obj)
        blueprint = Blueprint.model_validate(blueprint_obj)
        return blueprint, {'attempts': 2, 'raw': second_text}
