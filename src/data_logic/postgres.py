import os
import uuid
import base64
import io
import pypdf
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from src.models.base import Base
from src.models.chat_model import Chat
from src.models.message_model import Message
from src.models.user_model import User
from src.models.supplier_model import Supplier
from src.models.deal_memory_model import DealMemory
from src.models.action_queue_model import ActionQueueItem
from src.models.audit_log_model import AuditLog

load_dotenv()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_str() -> str:
    return _now().isoformat()


def _get_database_url() -> str:
    hostname = os.getenv("PSQL_HOST_NAME")
    database = os.getenv("PSQL_DATABASE")
    username = os.getenv("PSQL_USERNAME")
    password = os.getenv("PSQL_PASSWORD")
    port_id = os.getenv("PSQL_PORT_ID")

    if not all([hostname, database, username, password, port_id]):
        raise RuntimeError("PostgreSQL environment variables are not fully configured")

    return f"postgresql+psycopg2://{username}:{password}@{hostname}:{port_id}/{database}"


engine = create_engine(_get_database_url(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_database() -> None:
    #Base.metadata.drop_all(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)


try:
    initialize_database()
except Exception as exc:
    print(f"PostgreSQL initialization warning: {exc}")


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else _now_str(),
    }


def _serialize_chat(chat: Chat) -> dict:
    return {
        "id": str(chat.id),
        "user_id": str(chat.user_id),
        "title": chat.chat_name,
        "created_at": chat.created_at.isoformat() if chat.created_at else _now_str(),
        "updated_at": chat.modified_at.isoformat() if chat.modified_at else _now_str(),
    }


def _serialize_message(message: Message) -> dict:
    content = message.content
    if isinstance(content, dict):
        if "text" in content:
            content_value = content["text"]
        else:
            content_value = str(content)
    else:
        content_value = str(content)

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "role": message.sender_type,
        "content": content_value,
        "is_liked": message.is_liked,
        "created_at": message.sent_at.isoformat() if message.sent_at else _now_str(),
    }



def create_user(first_name: str, last_name: str, email: str, password: str, date_of_birth: str | None = None) -> dict:
    with SessionLocal() as session:
        # existing_user = session.query(User).filter(User.email == email).first()
        # if existing_user:
        #     return _serialize_user(existing_user)
        try:
            dob = datetime.fromisoformat(date_of_birth) if date_of_birth else _now()
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                date_of_birth=dob,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return _serialize_user(user)
        except IntegrityError:
            session.rollback()
            raise ValueError('Email Already Exists')




def login_user(email: str, password: str) -> dict:
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            #print(f"LOGIN DEBUG: User not found for email: {email}")
            raise ValueError("Invalid email or password")
        
        #print(f"LOGIN DEBUG: DB Password: [{user.password}] | Input Password: [{password}]")
        if user.password != password:
            #print("LOGIN DEBUG: Password mismatch!")
            raise ValueError("Invalid email or password")
            
        return _serialize_user(user)

def get_user(user_id: str) -> dict | None:
    with SessionLocal() as session:
        user = session.get(User, uuid.UUID(user_id))
        return _serialize_user(user) if user else None


def create_chat(user_id: str, title: str) -> dict:
    with SessionLocal() as session:
        chat = Chat(chat_name=title, user_id=uuid.UUID(user_id), is_pinned=False)
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return _serialize_chat(chat)


def list_user_chats(user_id: str) -> list[dict]:
    with SessionLocal() as session:
        chats = session.query(Chat).filter(Chat.user_id == uuid.UUID(user_id)).order_by(Chat.created_at.desc()).all()
        return [_serialize_chat(chat) for chat in chats]


def get_chat(chat_id: str) -> dict | None:
    with SessionLocal() as session:
        chat = session.get(Chat, uuid.UUID(chat_id))
        return _serialize_chat(chat) if chat else None


def delete_chat(chat_id: str) -> dict:
    with SessionLocal() as session:
        chat = session.get(Chat, uuid.UUID(chat_id))
        if not chat:
            return {"message": f"Chat {chat_id} deleted", "chat_id": chat_id}
        session.query(Message).filter(Message.chat_id == chat.id).delete(synchronize_session=False)
        session.delete(chat)
        session.commit()
        return {"message": f"Chat {chat_id} deleted", "chat_id": chat_id}


def create_message(chat_id: str, role: str, content: str, is_liked: bool | None = None) -> dict:
    with SessionLocal() as session:
        chat = session.get(Chat, uuid.UUID(chat_id))
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        message = Message(sender_type=role, is_liked=is_liked, content={"text": content}, chat_id=chat.id)
        session.add(message)
        chat.modified_at = _now()
        session.commit()
        session.refresh(message)
        return _serialize_message(message)


def list_messages(chat_id: str) -> list[dict]:
    with SessionLocal() as session:
        messages = session.query(Message).filter(Message.chat_id == uuid.UUID(chat_id)).order_by(Message.sent_at.asc()).all()
        return [_serialize_message(message) for message in messages]


def update_message_feedback(message_id: str, is_liked: bool | None) -> dict | None:
    with SessionLocal() as session:
        message = session.get(Message, uuid.UUID(message_id))
        if not message:
            return None
        message.is_liked = is_liked
        session.commit()
        session.refresh(message)
        return _serialize_message(message)


def delete_user(user_id: str) -> dict:
    with SessionLocal() as session:
        user = session.get(User, uuid.UUID(user_id))
        if not user:
            return {"message": f"User {user_id} deleted", "user_id": user_id}

        chats = session.query(Chat).filter(Chat.user_id == user.id).all()
        for chat in chats:
            session.query(Message).filter(Message.chat_id == chat.id).delete(synchronize_session=False)
            session.delete(chat)
        session.delete(user)
        session.commit()
        return {"message": f"User {user_id} deleted", "user_id": user_id}
    
def update_chat_title(chat_id: str, title: str) -> dict | None:
    with SessionLocal() as session:
        chat = session.get(Chat, uuid.UUID(chat_id))
        if not chat:
            return None
        chat.chat_name = title
        chat.modified_at = _now()
        session.commit()
        session.refresh(chat)
        return _serialize_chat(chat)

