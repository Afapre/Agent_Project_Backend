from __future__ import annotations

from datetime import datetime
from sqlalchemy import Date, Float, Integer, String, func,DateTime
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, UUIDPrimaryKey


class InventoryHistory(UUIDPrimaryKey, Base):
    __tablename__ = "inventory_sales_history"

    item_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    units_sold: Mapped[float] = mapped_column(Float, nullable=False)  # Consumption volume
    current_stock: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())