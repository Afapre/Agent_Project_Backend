from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from src.models.message_model import Message
    from src.models.user_model import User


class Chat(UUIDPrimaryKey, Base):
    __tablename__ = "chats"

    chat_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)