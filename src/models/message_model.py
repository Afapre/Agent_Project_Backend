from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from src.models.chat_model import Chat


class Message(UUIDPrimaryKey, Base):
    __tablename__ = "messages"

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sender_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_liked: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"), nullable=False)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
