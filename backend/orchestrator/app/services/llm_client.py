from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

GPT_CHAT_BASE_URL = os.getenv('GPT_CHAT_BASE_URL', 'http://localhost:7070').rstrip('/')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')


def _prefer_openai() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY.strip())


class LLMConnectionError(RuntimeError):
    pass


async def call_gpt_chat(messages: List[Dict[str, Any]], timeout_s: float = 60.0) -> Dict[str, Any]:
    # Enforce usage limits per request actor (if set by middleware).
    # This keeps the change localized and covers planner/generator/patch flows.
    from app.services.usage_context import (
        get_current_usage_action,
        get_current_usage_actor,
        get_current_usage_credits_charged,
        get_current_usage_plan_tier,
        set_current_usage_credits_charged,
    )
    from app.services.usage_store import (
        add_credits,
        add_tokens,
        credit_cost_for_action,
        ensure_under_limit,
        estimate_tokens_from_text,
    )

    actor = get_current_usage_actor()
    if actor:
        # Charge credits once per request action, even if multiple LLM calls happen.
        if not get_current_usage_credits_charged():
            action = get_current_usage_action()
            credits = credit_cost_for_action(action)
            if credits > 0:
                ensure_under_limit(actor=actor, plan_tier=get_current_usage_plan_tier(), credits_to_spend=credits)
                add_credits(actor=actor, credits=credits)
            set_current_usage_credits_charged(True)

    resp: Dict[str, Any]
    if _prefer_openai():
        resp = await _call_openai_chat(messages, timeout_s=timeout_s)
    else:
        resp = await _call_gateway_chat(messages, timeout_s=timeout_s)

    if actor:
        usage = resp.get("usage") if isinstance(resp, dict) else None
        tokens = 0
        if isinstance(usage, dict):
            total = usage.get("total_tokens")
            if isinstance(total, int):
                tokens = total
        if tokens <= 0:
            # Gateway mode: estimate tokens from prompt+reply.
            parts: list[str] = []
            for m in messages[-20:]:
                c = m.get("content") if isinstance(m, dict) else None
                if isinstance(c, str):
                    parts.append(c)
            reply = resp.get("reply") if isinstance(resp, dict) else None
            if isinstance(reply, str):
                parts.append(reply)
            tokens = estimate_tokens_from_text("\n".join(parts))
        if tokens > 0:
            add_tokens(actor=actor, tokens=tokens)

    return resp


async def _call_gateway_chat(messages: List[Dict[str, Any]], timeout_s: float) -> Dict[str, Any]:
    url = f"{GPT_CHAT_BASE_URL}/chat"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(url, json={'messages': messages})
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                snippet = response.text[:500]
                raise LLMConnectionError(
                    f"GPT chat service returned non-JSON at {url}. "
                    "Set OPENAI_API_KEY to call OpenAI directly. "
                    f"Body: {snippet}"
                ) from exc
    except (httpx.RequestError, OSError) as exc:
        raise LLMConnectionError(f"GPT chat service unreachable at {url}: {exc}") from exc


async def _call_openai_chat(messages: List[Dict[str, Any]], timeout_s: float) -> Dict[str, Any]:
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        'Authorization': f"Bearer {OPENAI_API_KEY}",
        'Content-Type': 'application/json',
    }
    payload: Dict[str, Any] = {
        'model': OPENAI_MODEL,
        'messages': messages,
        'temperature': 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ''
        raise LLMConnectionError(f"OpenAI API error: {exc}. Body: {body}") from exc
    except (httpx.RequestError, OSError) as exc:
        raise LLMConnectionError(f"OpenAI API unreachable at {url}: {exc}") from exc
    except ValueError as exc:
        raise LLMConnectionError(f"OpenAI API returned non-JSON at {url}: {exc}") from exc

    reply: Optional[str] = None
    try:
        choice0 = (data.get('choices') or [None])[0] or {}
        msg = choice0.get('message') or {}
        reply = msg.get('content')
    except Exception:
        reply = None

    if not isinstance(reply, str) or not reply.strip():
        raise LLMConnectionError('OpenAI API returned an empty response')

    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict):
        usage = {}

    # Normalize to the planner's expected shape.
    return {"reply": reply, "usage": usage}

