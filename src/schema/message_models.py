from pydantic import BaseModel


class MessageCreate(BaseModel):
    role: str
    content: str


class MessageFeedbackUpdate(BaseModel):
    is_liked: bool | None = None


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    is_liked: bool | None = None
    created_at: str | None = None
