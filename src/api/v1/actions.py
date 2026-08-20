from fastapi import APIRouter, HTTPException

from src.api.v1.chat_common import get_user_or_404
from src.data_logic.action_queue import (
    approve_action,
    execute_action,
    get_action,
    list_all_actions,
    list_pending_actions,
    reject_action,
)
from src.data_logic.audit_log import list_audit_logs, log_event
from src.schema.action_models import (
    ActionApproveRequest,
    ActionRejectRequest,
    ActionResponse,
    AuditLogResponse,
)

router = APIRouter()


@router.get("/chats/{chat_id}/pending-actions", response_model=list[ActionResponse])
async def get_pending_actions(chat_id: str, user_id: str):
    get_user_or_404(user_id)
    actions = list_pending_actions(user_id, chat_id)
    return [ActionResponse(**action) for action in actions]


@router.get("/users/{user_id}/pending-actions", response_model=list[ActionResponse])
async def get_user_pending_actions(user_id: str):
    get_user_or_404(user_id)
    actions = list_pending_actions(user_id)
    return [ActionResponse(**action) for action in actions]


@router.get("/users/{user_id}/actions", response_model=list[ActionResponse])
async def get_user_actions(user_id: str, status: str | None = None, limit: int = 200):
    """Full action history for a user, across all statuses (pending, approved, rejected, executed, edited)."""
    get_user_or_404(user_id)
    actions = list_all_actions(user_id, status=status, limit=limit)
    return [ActionResponse(**action) for action in actions]


@router.post("/actions/{action_id}/approve", response_model=ActionResponse)
async def approve_pending_action(action_id: str, payload: ActionApproveRequest):
    get_user_or_404(payload.user_id)
    action = approve_action(action_id, payload.user_id, payload.edit_payload)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    exec_result = execute_action(action)
    log_event(
        event_type="human_decision",
        user_id=payload.user_id,
        chat_id=action.get("chat_id"),
        tool_name=action["action_type"],
        details={"action_id": action_id, "execution_result": exec_result},
        human_decision="approved" if not payload.edit_payload else "edited_and_approved",
        reasoning=action.get("reasoning"),
        document_refs=action.get("source_documents", []),
    )

    return ActionResponse(**action, execution_result=exec_result)


@router.post("/actions/{action_id}/reject", response_model=ActionResponse)
async def reject_pending_action(action_id: str, payload: ActionRejectRequest):
    get_user_or_404(payload.user_id)
    action = reject_action(action_id, payload.user_id, payload.reason)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found or already resolved")

    log_event(
        event_type="human_decision",
        user_id=payload.user_id,
        chat_id=action.get("chat_id"),
        tool_name=action["action_type"],
        details={"action_id": action_id, "rejection_reason": payload.reason},
        human_decision="rejected",
        reasoning=payload.reason,
        document_refs=action.get("source_documents", []),
    )

    return ActionResponse(**action)


@router.get("/actions/{action_id}", response_model=ActionResponse)
async def get_action_detail(action_id: str):
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return ActionResponse(**action)


@router.get("/users/{user_id}/audit-log", response_model=list[AuditLogResponse])
async def get_audit_log(user_id: str, chat_id: str | None = None, limit: int = 100):
    get_user_or_404(user_id)
    entries = list_audit_logs(user_id=user_id, chat_id=chat_id, limit=limit)
    return [AuditLogResponse(**entry) for entry in entries]
