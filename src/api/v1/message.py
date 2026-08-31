from fastapi import APIRouter, HTTPException

from src.api.v1.chat_common import get_chat_or_404, get_user_or_404, run_clara_agent
from src.data_logic.doc_processor import PDFProcessor
from src.data_logic.postgres import create_message as db_create_message
from src.data_logic.postgres import list_messages as db_list_messages
from src.data_logic.postgres import update_message_feedback as db_update_message_feedback
from src.exceptions.harmful_exceptions import HarmfulContentError
from src.schema.chat_models import ChatRequest, ChatResult
from src.schema.message_models import MessageCreate, MessageFeedbackUpdate, MessageResponse

router = APIRouter()


@router.post(path="/message", response_model=ChatResult)
async def chat_with_clara(payload: ChatRequest):
    try:
        get_user_or_404(payload.user_id)
        if payload.chat_id:
            get_chat_or_404(payload.chat_id)

        if not payload.prompt or not payload.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        processor = PDFProcessor()
        retrieved_context = processor.retrieve_document_context(
            payload.prompt,
            user_id=payload.user_id,
            chat_id=payload.chat_id,
            document_ids=payload.document_ids,
        )

        combined_context: list[str] = []
        if payload.context_text and payload.context_text.strip():
            combined_context.append(payload.context_text.strip())
        if retrieved_context.strip():
            combined_context.append(retrieved_context.strip())

        final_text, audio_base64, pending_actions, audit_entries = await run_clara_agent(
            prompt=payload.prompt,
            history=payload.history or None,
            chat_id=payload.chat_id,
            context_text="\n\n".join(combined_context) if combined_context else None,
            user_id=payload.user_id,
            document_ids=payload.document_ids,
        )

        user_message = db_create_message(
            chat_id=payload.chat_id,
            role="user",
            content=payload.prompt,
        )
        assistant_message = db_create_message(
            chat_id=payload.chat_id,
            role="assistant",
            content=final_text,
        )

        return ChatResult(
            message_id=assistant_message["id"],
            user_message_id=user_message["id"],
            user_id=payload.user_id,
            chat_id=payload.chat_id,
            response=final_text,
            content=final_text,
            audio=audio_base64,
            created_at=None,
            pending_actions=pending_actions,
            audit_entries=audit_entries,
        )
    except HarmfulContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
async def create_message(chat_id: str, payload: MessageCreate):
    message = db_create_message(
        chat_id=chat_id,
        role=payload.role,
        content=payload.content,
    )
    return MessageResponse(**message)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def list_messages(chat_id: str):
    messages = db_list_messages(chat_id)
    return [MessageResponse(**message) for message in messages]


@router.patch("/messages/{message_id}/like", response_model=MessageResponse)
async def update_message_feedback(message_id: str, payload: MessageFeedbackUpdate):
    updated = db_update_message_feedback(message_id, payload.is_liked)
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageResponse(**updated)
