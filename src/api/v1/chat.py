import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from src.addons.text_to_speech import text_to_speech
from src.core.agent_logic import get_clara_agent
from src.data_logic.doc_processor import PDFProcessor
from src.data_logic.postgres import (
    create_chat as db_create_chat,
    create_message as db_create_message,
    create_user as db_create_user,
    login_user as db_login_user,
    delete_chat as db_delete_chat,
    delete_user as db_delete_user,
    get_chat as db_get_chat,
    get_user as db_get_user,
    list_messages as db_list_messages,
    list_user_chats as db_list_user_chats,
    update_message_feedback as db_update_message_feedback,
)
from src.exceptions.harmful_exceptions import HarmfulContentError
from src.schema.chat_models import (
    ChatCreate,
    ChatRequest,
    ChatResponse,
    ChatSummary,
    MessageCreate,
    MessageFeedbackUpdate,
    MessageResponse,
    UserCreate,
    UserLoginRequest,
    UserResponse,
)
from src.tools.tools_definition import get_tools

load_dotenv()

router = APIRouter()


def _normalize_user_name(payload: UserCreate) -> tuple[str, str]:
    if payload.first_name is not None or payload.last_name is not None:
        first_name = (payload.first_name or "").strip()
        last_name = (payload.last_name or "").strip()
        return first_name, last_name

    full_name = (payload.name or "").strip()
    if not full_name:
        return "", ""

    parts = full_name.split(maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _get_user(user_id: str) -> dict:
    user = db_get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_chat(chat_id: str) -> dict:
    chat = db_get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def _build_formatted_history(history: list[dict] | None = None, chat_id: str | None = None) -> list:
    formatted_history = []

    if chat_id:
        for message in db_list_messages(chat_id):
            if message["role"] == "user":
                formatted_history.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                formatted_history.append(AIMessage(content=message["content"]))

    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                continue
            if role in {"user", "human"}:
                formatted_history.append(HumanMessage(content=content))
            elif role in {"assistant", "ai"}:
                formatted_history.append(AIMessage(content=content))

    return formatted_history


async def _run_clara_agent(prompt: str, history: list[dict] | None = None, chat_id: str | None = None) -> tuple[str, str | None]:
    google_key = os.getenv("GOOGLE_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not google_key:
        raise HTTPException(status_code=500, detail="Missing GOOGLE_API_KEY environment variable.")

    processor = PDFProcessor()
    collection = processor.collection
    tools = get_tools(collection, tavily_key)
    agent = get_clara_agent(tools, google_key)

    formatted_history = _build_formatted_history(history=history, chat_id=chat_id)
    formatted_history.append(HumanMessage(content=prompt.strip()))

    response = agent.invoke({"messages": formatted_history})

    if isinstance(response, dict) and "messages" in response:
        message_list = response["messages"]
        ai_msg = None
        for msg in reversed(message_list):
            if hasattr(msg, "type") and msg.type == "ai":
                ai_msg = msg
                break
            if hasattr(msg, "__class__") and msg.__class__.__name__ == "AIMessage":
                ai_msg = msg
                break
        raw_content = ai_msg.content if ai_msg else message_list[-1].content
    else:
        raw_content = response.content if hasattr(response, "content") else response

    final_text = ""
    if isinstance(raw_content, list):
        for item in raw_content:
            if isinstance(item, dict) and "text" in item:
                final_text += item["text"]
            elif isinstance(item, str):
                final_text += item
    else:
        final_text = str(raw_content).strip()

    audio_base64 = text_to_speech(final_text)
    return final_text.strip(), audio_base64 if audio_base64 else None


@router.post(path="/message", response_model=ChatResponse)
async def chat_with_clara(payload: ChatRequest):
    """
    Submits a message prompt along with conversational history to CLARA
    and stores the exchange in PostgreSQL-backed chat state.
    """
    try:
        user_id = payload.user_id or "anonymous"
        if payload.user_id:
            _get_user(payload.user_id)

        chat_id = payload.chat_id
        if not chat_id:
            created_chat = db_create_chat(user_id, (payload.title or payload.prompt[:40]).strip())
            chat_id = created_chat["id"]
        else:
            chat = _get_chat(chat_id)
            if chat["user_id"] != user_id and user_id != "anonymous":
                raise HTTPException(status_code=403, detail="Chat does not belong to this user")

        final_text, audio_base64 = await _run_clara_agent(payload.prompt, history=payload.history, chat_id=chat_id)

        db_create_message(chat_id, "user", payload.prompt.strip())
        assistant_message = db_create_message(chat_id, "assistant", final_text)

        return ChatResponse(
            response=final_text,
            audio=audio_base64,
            user_id=user_id,
            chat_id=chat_id,
            message_id=assistant_message["id"],
        )

    except HarmfulContentError as e:
        raise HTTPException(status_code=403, detail=f"Harmful Content Execution Failure: {str(e)}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Agent Execution Failure: {str(e)}")


@router.post("/users", response_model=UserResponse)
async def create_user(payload: UserCreate):
    first_name, last_name = _normalize_user_name(payload)
    try:
        return db_create_user(
                first_name=first_name,
                last_name=last_name,
                email=payload.email,
                password=payload.password or "",
                date_of_birth=payload.date_of_birth,
            )
    except ValueError as e:
        if str(e)=="Email Already Exists":
            raise HTTPException(status_code=409, detail='Email already registered to another account.')
    


@router.post("/users/login", response_model=UserResponse)
async def login_user(payload: UserLoginRequest):
    try:
        return db_login_user(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    return _get_user(user_id)


@router.post("/chats", response_model=ChatSummary)
async def create_chat(payload: ChatCreate):
    _get_user(payload.user_id)
    return db_create_chat(payload.user_id, payload.title or "New chat")


@router.get("/users/{user_id}/chats", response_model=list[ChatSummary])
async def list_user_chats(user_id: str):
    _get_user(user_id)
    return db_list_user_chats(user_id)


@router.get("/chats/{chat_id}", response_model=ChatSummary)
async def get_chat(chat_id: str):
    return _get_chat(chat_id)


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    _get_chat(chat_id)
    return db_delete_chat(chat_id)


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
async def create_message(chat_id: str, payload: MessageCreate):
    _get_chat(chat_id)
    return db_create_message(chat_id, payload.role, payload.content)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def list_messages(chat_id: str):
    _get_chat(chat_id)
    return db_list_messages(chat_id)


@router.patch("/messages/{message_id}/like", response_model=MessageResponse)
async def update_message_feedback(message_id: str, payload: MessageFeedbackUpdate):
    message = db_update_message_feedback(message_id, payload.is_liked)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    _get_user(user_id)
    return db_delete_user(user_id)
