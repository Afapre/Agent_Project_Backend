from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from src.models.chat_model import Chat
    from src.models.supplier_model import Supplier


class User(UUIDPrimaryKey, Base):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    suppliers: Mapped[List["Supplier"]] = relationship(
        "Supplier", back_populates="user", cascade="all, delete-orphan"
    )
