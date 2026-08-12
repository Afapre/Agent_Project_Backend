from typing import Literal,Optional

from pydantic import BaseModel, Field


# class UserCreate(BaseModel):
#     first_name: str | None = None
#     last_name: str | None = None
#     name: str | None = None
#     email: str = Field(..., min_length=3)
#     password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
#     date_of_birth: str | None = None
class UserCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    email: str
    password: str
    date_of_birth: str | None = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str | None = None


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