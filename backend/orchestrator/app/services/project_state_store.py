from __future__ import annotations

from datetime import datetime
from typing import Tuple

from app.db import db_enabled, session_scope
from app.db_models import Project as ProjectRow
from app.services import project_state_store_file


def get_project_state_payload(project_id: str) -> Tuple[datetime, dict, dict] | None:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                return None
            blueprint = row.blueprint if isinstance(row.blueprint, dict) else {}
            plan = row.plan if isinstance(row.plan, dict) else {}
            return row.updated_at, blueprint, plan

    raw = project_state_store_file.get_state(project_id)
    if not raw:
        return None

    updated_at_str = raw.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_str) if isinstance(updated_at_str, str) else datetime.utcnow()
    except Exception:
        updated_at = datetime.utcnow()

    blueprint_raw = raw.get("blueprint")
    plan_raw = raw.get("plan")
    blueprint: dict = blueprint_raw if isinstance(blueprint_raw, dict) else {}
    plan: dict = plan_raw if isinstance(plan_raw, dict) else {}

    return updated_at, blueprint, plan


def put_project_state_payload(project_id: str, *, blueprint: dict | None = None, plan: dict | None = None) -> Tuple[datetime, dict, dict]:
    if db_enabled():
        with session_scope() as session:
            row = session.get(ProjectRow, project_id)
            if row is None:
                raise ValueError("Project not found")
            if blueprint is not None:
                row.blueprint = blueprint
            if plan is not None:
                row.plan = plan
            session.flush()

            blueprint_out = row.blueprint if isinstance(row.blueprint, dict) else {}
            plan_out = row.plan if isinstance(row.plan, dict) else {}
            return row.updated_at, blueprint_out, plan_out

    raw = project_state_store_file.put_state(project_id, blueprint=blueprint, plan=plan)
    updated_at_str = raw.get("updated_at")
    try:
        updated_at = datetime.fromisoformat(updated_at_str) if isinstance(updated_at_str, str) else datetime.utcnow()
    except Exception:
        updated_at = datetime.utcnow()

    blueprint_out_raw = raw.get("blueprint")
    plan_out_raw = raw.get("plan")
    blueprint_out: dict = blueprint_out_raw if isinstance(blueprint_out_raw, dict) else {}
    plan_out: dict = plan_out_raw if isinstance(plan_out_raw, dict) else {}

    return updated_at, blueprint_out, plan_out
