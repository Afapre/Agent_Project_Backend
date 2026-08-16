from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    chat_id: Mapped[UUID | None] = mapped_column(ForeignKey("chats.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    document_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    human_decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
