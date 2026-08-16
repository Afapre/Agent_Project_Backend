from pydantic import BaseModel


class ActionApproveRequest(BaseModel):
    user_id: str
    edit_payload: dict | None = None


class ActionRejectRequest(BaseModel):
    user_id: str
    reason: str | None = None


class ActionResponse(BaseModel):
    id: str
    user_id: str
    chat_id: str | None = None
    action_type: str
    payload: dict
    authority_tier: str
    status: str
    reasoning: str | None = None
    source_documents: list[str] = []
    edit_payload: dict | None = None
    rejection_reason: str | None = None
    resolved_by: str | None = None
    created_at: str | None = None
    resolved_at: str | None = None
    execution_result: dict | None = None


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    chat_id: str | None = None
    event_type: str
    tool_name: str | None = None
    details: dict = {}
    document_refs: list[str] = []
    human_decision: str | None = None
    reasoning: str | None = None
    created_at: str | None = None
