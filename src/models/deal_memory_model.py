from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from src.models.supplier_model import Supplier


class DealMemory(UUIDPrimaryKey, Base):
    __tablename__ = "deal_memories"

    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    contract_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_history: Mapped[list[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    dispute_log: Mapped[list[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    compliance_status: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    relationship_health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_documents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="deal_memories")
