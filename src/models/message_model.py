from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import String,DateTime,Boolean,JSON,ForeignKey,func
from datetime import datetime
from typing import Any,Dict
from uuid import UUID
from src.models.base import Base,UUIDPrimaryKey


class Message(UUIDPrimaryKey, Base):
    __tablename__ = "messages"

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sender_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_liked: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    chat_id: Mapped[UUID] = mapped_column(ForeignKey("chats.id"), nullable=False)

    # Bidirectional relationship
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
