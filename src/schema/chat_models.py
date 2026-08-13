from pydantic import BaseModel

# Backward-compatible re-exports while the codebase transitions to split schema files.
from src.schema.message_models import MessageCreate, MessageFeedbackUpdate, MessageResponse
from src.schema.user_models import UserCreate, UserLoginRequest, UserResponse


class ChatRequest(BaseModel):
    user_id: str
    chat_id: str
    prompt: str
    history: list[dict] | None = None
    context_text: str | None = None
    document_ids: list[str] | None = None


class ChatResponse(BaseModel):
    id: str
    user_id: str
    chat_id: str
    role: str
    content: str
    created_at: str | None = None


class ChatResult(BaseModel):
    message_id: str
    user_message_id: str | None = None
    user_id: str
    chat_id: str
    response: str
    content: str
    audio: str | None = None
    created_at: str | None = None


class ChatCreate(BaseModel):
    user_id: str
    title: str | None = None


class ChatUpdate(BaseModel):
    title: str


class ChatSummary(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
