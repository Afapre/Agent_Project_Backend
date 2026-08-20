"""Authority tiers and action queue management."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from src.data_logic.postgres import SessionLocal
from src.models.action_queue_model import ActionQueueItem

# routine: auto-execute (reminders, internal notes)
# standard: user confirmation (spreadsheets, PDFs, calendar)
# binding: manager sign-off (emails to suppliers, PO approval, contract amendments)
AUTHORITY_TIERS = {
    "routine": 0,
    "standard": 1,
    "binding": 2,
}

ACTION_TIER_MAP = {
    "schedule_reminder": "routine",
    "internal_note": "routine",
    "create_spreadsheet": "standard",
    "generate_pdf_memo": "standard",
    "schedule_calendar_event": "standard",
    "present_for_review": "routine",
    "draft_email": "binding",
    "send_rfp": "binding",
    "approve_po": "binding",
    "contract_amendment": "binding",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_action(item: ActionQueueItem) -> dict:
    return {
        "id": str(item.id),
        "user_id": str(item.user_id),
        "chat_id": str(item.chat_id) if item.chat_id else None,
        "action_type": item.action_type,
        "payload": item.payload,
        "authority_tier": item.authority_tier,
        "status": item.status,
        "reasoning": item.reasoning,
        "source_documents": item.source_documents or [],
        "edit_payload": item.edit_payload,
        "rejection_reason": item.rejection_reason,
        "resolved_by": str(item.resolved_by) if item.resolved_by else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
    }


def get_tier_for_action(action_type: str) -> str:
    return ACTION_TIER_MAP.get(action_type, "standard")


def should_auto_execute(authority_tier: str) -> bool:
    return AUTHORITY_TIERS.get(authority_tier, 1) == AUTHORITY_TIERS["routine"]


def queue_action(
    user_id: str,
    action_type: str,
    payload: dict[str, Any],
    reasoning: str,
    source_documents: list[str] | None = None,
    chat_id: str | None = None,
    authority_tier: str | None = None,
) -> dict:
    tier = authority_tier or get_tier_for_action(action_type)
    status = "executed" if should_auto_execute(tier) else "pending"

    with SessionLocal() as session:
        item = ActionQueueItem(
            user_id=uuid.UUID(user_id),
            chat_id=uuid.UUID(chat_id) if chat_id else None,
            action_type=action_type,
            payload=payload,
            authority_tier=tier,
            status=status,
            reasoning=reasoning,
            source_documents=source_documents or [],
            resolved_at=_now() if status == "executed" else None,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return _serialize_action(item)


def list_pending_actions(user_id: str, chat_id: str | None = None) -> list[dict]:
    with SessionLocal() as session:
        query = session.query(ActionQueueItem).filter(
            ActionQueueItem.user_id == uuid.UUID(user_id),
            ActionQueueItem.status == "pending",
        )
        if chat_id:
            query = query.filter(ActionQueueItem.chat_id == uuid.UUID(chat_id))
        items = query.order_by(ActionQueueItem.created_at.desc()).all()
        return [_serialize_action(item) for item in items]


def list_all_actions(user_id: str, status: str | None = None, limit: int = 200) -> list[dict]:
    """Return the full action history (any status) for a user, most recent first."""
    with SessionLocal() as session:
        query = session.query(ActionQueueItem).filter(ActionQueueItem.user_id == uuid.UUID(user_id))
        if status:
            query = query.filter(ActionQueueItem.status == status)
        items = query.order_by(ActionQueueItem.created_at.desc()).limit(limit).all()
        return [_serialize_action(item) for item in items]


def get_action(action_id: str) -> dict | None:
    with SessionLocal() as session:
        item = session.get(ActionQueueItem, uuid.UUID(action_id))
        return _serialize_action(item) if item else None


def approve_action(action_id: str, user_id: str, edit_payload: dict | None = None) -> dict | None:
    with SessionLocal() as session:
        item = session.get(ActionQueueItem, uuid.UUID(action_id))
        if not item or item.status != "pending":
            return None
        item.status = "approved"
        item.resolved_by = uuid.UUID(user_id)
        item.resolved_at = _now()
        if edit_payload:
            item.edit_payload = edit_payload
            item.status = "edited"
        session.commit()
        session.refresh(item)
        return _serialize_action(item)


def reject_action(action_id: str, user_id: str, reason: str | None = None) -> dict | None:
    with SessionLocal() as session:
        item = session.get(ActionQueueItem, uuid.UUID(action_id))
        if not item or item.status != "pending":
            return None
        item.status = "rejected"
        item.resolved_by = uuid.UUID(user_id)
        item.resolved_at = _now()
        item.rejection_reason = reason
        session.commit()
        session.refresh(item)
        return _serialize_action(item)


def execute_action(action: dict) -> dict:
    """Simulate execution of an approved action. Returns execution result."""
    action_type = action["action_type"]
    payload = action.get("edit_payload") or action.get("payload") or {}

    executors = {
        "draft_email": _execute_draft_email,
        "send_rfp": _execute_send_rfp,
        "create_spreadsheet": _execute_create_spreadsheet,
        "generate_pdf_memo": _execute_generate_pdf,
        "schedule_calendar_event": _execute_schedule_calendar,
        "schedule_reminder": _execute_schedule_reminder,
        "present_for_review": _execute_present_for_review,
        "approve_po": _execute_approve_po,
        "contract_amendment": _execute_contract_amendment,
        "internal_note": _execute_internal_note,
    }

    executor = executors.get(action_type, _execute_generic)
    result = executor(payload)
    result["action_id"] = action["id"]
    result["action_type"] = action_type
    return result


def _execute_draft_email(payload: dict) -> dict:
    return {
        "status": "ready_to_send",
        "from_email": payload.get("from_email", ""),
        "message": f"Email drafted to {payload.get('recipients', 'recipients')}",
        "subject": payload.get("subject", ""),
        "body_preview": (payload.get("body", "")[:200] + "...") if payload.get("body") else "",
    }


def _execute_send_rfp(payload: dict) -> dict:
    vendors = payload.get("vendors", [])
    return {
        "status": "sent",
        "from_email": payload.get("from_email", ""),
        "message": f"RFP invitations sent to {len(vendors)} vendor(s): {', '.join(vendors)}",
    }


def _execute_create_spreadsheet(payload: dict) -> dict:
    return {
        "status": "created",
        "message": f"Spreadsheet '{payload.get('title', 'Evaluation Scorecard')}' created",
        "columns": payload.get("columns", []),
        "criteria_weights": payload.get("criteria_weights", {}),
        "download_path": f"/exports/{payload.get('title', 'scorecard').replace(' ', '_').lower()}.xlsx",
    }


def _execute_generate_pdf(payload: dict) -> dict:
    return {
        "status": "generated",
        "message": f"PDF memo '{payload.get('title', 'Approval Memo')}' generated",
        "sections": payload.get("sections", []),
        "download_path": f"/exports/{payload.get('title', 'memo').replace(' ', '_').lower()}.pdf",
    }


def _execute_schedule_calendar(payload: dict) -> dict:
    return {
        "status": "scheduled",
        "message": f"Meeting '{payload.get('title', 'Review')}' scheduled for {payload.get('datetime', 'TBD')}",
        "attendees": payload.get("attendees", []),
    }


def _execute_schedule_reminder(payload: dict) -> dict:
    return {
        "status": "scheduled",
        "message": f"Reminder set for {payload.get('datetime', 'TBD')}: {payload.get('message', '')}",
    }


def _execute_present_for_review(payload: dict) -> dict:
    return {
        "status": "presented",
        "message": "Package presented for user review",
        "items": payload.get("items", []),
    }


def _execute_approve_po(payload: dict) -> dict:
    return {
        "status": "approved",
        "message": f"PO {payload.get('po_number', 'N/A')} approved for {payload.get('amount', 'N/A')}",
    }


def _execute_contract_amendment(payload: dict) -> dict:
    return {
        "status": "drafted",
        "message": f"Contract amendment drafted for {payload.get('supplier', 'supplier')}",
    }


def _execute_internal_note(payload: dict) -> dict:
    return {"status": "saved", "message": "Internal note saved"}


def _execute_generic(payload: dict) -> dict:
    return {"status": "executed", "message": "Action executed", "payload": payload}
