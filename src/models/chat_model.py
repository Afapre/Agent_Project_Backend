from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import String,DateTime,func,Boolean,text,ForeignKey
from datetime import datetime
from src.models.base import Base,UUIDPrimaryKey
from uuid import UUID
from typing import List,Any,Dict

class Chat(UUIDPrimaryKey,Base):
    __tablename__="chats"

    chat_name:Mapped[str]=mapped_column(String(100),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    modified_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    is_pinned:Mapped[bool]=mapped_column(Boolean,nullable=False,server_default=text('0'))

    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

    user_id:Mapped[UUID]=mapped_column(ForeignKey("users.id"),nullable=False)