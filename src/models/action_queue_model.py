from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDPrimaryKey


class ActionQueueItem(UUIDPrimaryKey, Base):
    __tablename__ = "action_queue"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    chat_id: Mapped[UUID | None] = mapped_column(ForeignKey("chats.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    authority_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_documents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    edit_payload: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
