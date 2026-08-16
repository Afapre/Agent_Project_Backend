from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from src.models.deal_memory_model import DealMemory
    from src.models.user_model import User


class Supplier(UUIDPrimaryKey, Base):
    __tablename__ = "suppliers"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="suppliers")
    deal_memories: Mapped[list["DealMemory"]] = relationship(
        "DealMemory", back_populates="supplier", cascade="all, delete-orphan"
    )
