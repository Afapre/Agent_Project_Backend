from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import String,DateTime,func
from datetime import datetime
from src.models.base import Base,UUIDPrimaryKey
from typing import List,Any,Dict

class User(UUIDPrimaryKey,Base):
    __tablename__="users"

    first_name:Mapped[str]=mapped_column(String(100),nullable=False)
    last_name:Mapped[str]=mapped_column(String(100),nullable=False)
    email:Mapped[str]=mapped_column(String(100),nullable=False,unique=True)
    date_of_birth:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())

    # Bidirectional relationship with cascade delete
    chats: Mapped[List["Chat"]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
