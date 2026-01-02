from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.db_models import ProjectChatMessage as ProjectChatMessageRow
from app.services.llm_client import LLMConnectionError, call_gpt_chat

router = APIRouter()


ChatRole = Literal['system', 'user', 'assistant']


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class ProjectChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class ProjectChatHistoryItem(BaseModel):
    role: ChatRole
    content: str
    created_at: datetime


class ProjectChatHistoryResponse(BaseModel):
    project_id: str
    messages: List[ProjectChatHistoryItem] = Field(default_factory=list)


def _coerce_role(value: str) -> ChatRole:
    if value in ('system', 'user', 'assistant'):
        return value  # type: ignore[return-value]
    return 'assistant'


CHAT_SYSTEM_PROMPT = """You are CodeLaunchAI, an expert product designer + full-stack engineer.

Goal:
- Help the user clarify what they want to build.

Rules:
- Ask 1–3 clarifying questions that materially change the blueprint or code.
- Keep questions short, practical, and specific.
- If you already have enough info, confirm what you'll build and propose the next step.
- Do not output code.
"""


@router.post('/chat', response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    # Always include our system message first.
    messages: List[Dict[str, Any]] = [{'role': 'system', 'content': CHAT_SYSTEM_PROMPT}]

    for m in body.messages[-20:]:
        messages.append({'role': m.role, 'content': m.content})

    if body.context:
        messages.append({'role': 'system', 'content': f"Context (JSON): {body.context}"})

    try:
        resp = await call_gpt_chat(messages, timeout_s=45.0)
        reply = resp.get('reply') if isinstance(resp, dict) else None
        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError('Empty reply from LLM')
        return ChatResponse(reply=reply.strip(), meta={'offline': False})
    except LLMConnectionError as exc:
        # Minimal offline fallback so UI stays usable.
        fallback = (
            "I can help. A few quick questions to get this right:\n"
            "1) What pages/sections do you need?\n"
            "2) Any integrations (payments, email, auth)?\n"
            "3) What style/brand vibe should it follow?"
        )
        return ChatResponse(reply=fallback, meta={'offline': True, 'reason': str(exc)[:300]})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Chat failed: {exc}') from exc


def _load_recent_project_messages(project_id: str, limit: int = 20) -> List[ProjectChatMessageRow]:
    if not db_enabled():
        return []
    with session_scope() as session:
        rows = (
            session.query(ProjectChatMessageRow)
            .filter(ProjectChatMessageRow.project_id == project_id)
            .order_by(ProjectChatMessageRow.created_at.desc(), ProjectChatMessageRow.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))


def _append_project_messages(project_id: str, items: List[dict]) -> None:
    if not db_enabled():
        return
    with session_scope() as session:
        project = session.get(ProjectRow, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail='Project not found')

        for item in items:
            session.add(
                ProjectChatMessageRow(
                    project_id=project_id,
                    role=str(item.get('role')),
                    content=str(item.get('content')),
                )
            )


@router.get('/projects/{project_id}/chat/history', response_model=ProjectChatHistoryResponse)
def get_project_chat_history(project_id: str) -> ProjectChatHistoryResponse:
    if not db_enabled():
        raise HTTPException(status_code=501, detail='Postgres not configured (set DATABASE_URL)')

    rows = _load_recent_project_messages(project_id, limit=50)
    return ProjectChatHistoryResponse(
        project_id=project_id,
        messages=[
            ProjectChatHistoryItem(role=_coerce_role(row.role), content=row.content, created_at=row.created_at)
            for row in rows
        ],
    )


@router.post('/projects/{project_id}/chat', response_model=ChatResponse)
async def chat_for_project(project_id: str, body: ProjectChatRequest) -> ChatResponse:
    # We still allow chat to work without Postgres, but persistence is only enabled with DB.
    history = _load_recent_project_messages(project_id, limit=20)

    messages: List[Dict[str, Any]] = [{'role': 'system', 'content': CHAT_SYSTEM_PROMPT}]
    for row in history:
        messages.append({'role': row.role, 'content': row.content})
    messages.append({'role': 'user', 'content': body.message})
    if body.context:
        messages.append({'role': 'system', 'content': f"Context (JSON): {body.context}"})

    try:
        resp = await call_gpt_chat(messages, timeout_s=45.0)
        reply = resp.get('reply') if isinstance(resp, dict) else None
        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError('Empty reply from LLM')

        _append_project_messages(
            project_id,
            [
                {'role': 'user', 'content': body.message},
                {'role': 'assistant', 'content': reply.strip()},
            ],
        )
        return ChatResponse(reply=reply.strip(), meta={'offline': False})
    except LLMConnectionError as exc:
        fallback = (
            "I can help. A few quick questions to get this right:\n"
            "1) What pages/sections do you need?\n"
            "2) Any integrations (payments, email, auth)?\n"
            "3) What style/brand vibe should it follow?"
        )
        _append_project_messages(
            project_id,
            [
                {'role': 'user', 'content': body.message},
                {'role': 'assistant', 'content': fallback},
            ],
        )
        return ChatResponse(reply=fallback, meta={'offline': True, 'reason': str(exc)[:300]})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Chat failed: {exc}') from exc
