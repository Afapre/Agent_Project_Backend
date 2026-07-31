from sqlalchemy.orm import DeclarativeBase
from uuid import UUID
from sqlalchemy.orm import Mapped,mapped_column
import uuid

class Base(DeclarativeBase):
    pass

class UUIDPrimaryKey:
    id:Mapped[UUID]=mapped_column(UUID,primary_key=True,default=uuid.uuid4)