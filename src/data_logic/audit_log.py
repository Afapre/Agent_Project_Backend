"""Audit logging for procurement compliance."""

from __future__ import annotations

import uuid
from typing import Any

from src.data_logic.postgres import SessionLocal
from src.models.audit_log_model import AuditLog


def log_event(
    event_type: str,
    user_id: str | None = None,
    chat_id: str | None = None,
    tool_name: str | None = None,
    details: dict[str, Any] | None = None,
    document_refs: list[str] | None = None,
    human_decision: str | None = None,
    reasoning: str | None = None,
) -> dict:
    with SessionLocal() as session:
        entry = AuditLog(
            user_id=uuid.UUID(user_id) if user_id else None,
            chat_id=uuid.UUID(chat_id) if chat_id else None,
            event_type=event_type,
            tool_name=tool_name,
            details=details or {},
            document_refs=document_refs or [],
            human_decision=human_decision,
            reasoning=reasoning,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return _serialize(entry)


def _serialize(entry: AuditLog) -> dict:
    return {
        "id": str(entry.id),
        "user_id": str(entry.user_id) if entry.user_id else None,
        "chat_id": str(entry.chat_id) if entry.chat_id else None,
        "event_type": entry.event_type,
        "tool_name": entry.tool_name,
        "details": entry.details,
        "document_refs": entry.document_refs or [],
        "human_decision": entry.human_decision,
        "reasoning": entry.reasoning,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def list_audit_logs(
    user_id: str | None = None,
    chat_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with SessionLocal() as session:
        query = session.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == uuid.UUID(user_id))
        if chat_id:
            query = query.filter(AuditLog.chat_id == uuid.UUID(chat_id))
        entries = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [_serialize(entry) for entry in entries]
