import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.v1.chat_common import extract_document_text, get_chat_or_404, get_user_or_404
from src.data_logic.doc_processor import PDFProcessor
from src.data_logic.postgres import create_chat as db_create_chat
from src.data_logic.postgres import delete_chat as db_delete_chat
from src.data_logic.postgres import list_user_chats as db_list_user_chats
from src.data_logic.postgres import update_chat_title as db_update_chat_title
from src.schema.chat_models import ChatCreate, ChatSummary, ChatUpdate

router = APIRouter()


@router.post("/documents/upload-context")
async def upload_document_context(
	file: UploadFile = File(...),
	user_id: str | None = Form(default=None),
	chat_id: str | None = Form(default=None),
):
	if user_id:
		get_user_or_404(user_id)
	if chat_id:
		get_chat_or_404(chat_id)

	extracted_text = await extract_document_text(file)
	if not extracted_text.strip():
		raise HTTPException(status_code=422, detail="No readable text could be extracted from the uploaded file")

	filename = file.filename or "uploaded-file"
	extension = os.path.splitext(filename.lower())[1]
	document_id = str(uuid.uuid4())
	processor = PDFProcessor()
	chunk_count = processor.index_document_text(
		extracted_text,
		document_id=document_id,
		filename=filename,
		user_id=user_id,
		chat_id=chat_id,
		source_type="image" if extension in {".png", ".jpg", ".jpeg", ".webp"} else "document",
	)

	if chunk_count == 0:
		raise HTTPException(status_code=422, detail="The uploaded file did not produce any retrievable content")

	return {
		"id": document_id,
		"filename": filename,
		"user_id": user_id,
		"chat_id": chat_id,
		"char_count": len(extracted_text),
		"chunk_count": chunk_count,
		"status": "indexed",
	}


@router.get("/chats/{chat_id}/documents")
async def list_chat_documents(chat_id: str, user_id: str | None = None):
	get_chat_or_404(chat_id)
	if user_id:
		get_user_or_404(user_id)

	processor = PDFProcessor()
	return processor.list_chat_documents(chat_id=chat_id, user_id=user_id)


@router.delete("/chats/{chat_id}/documents/{document_id}")
async def delete_chat_document(chat_id: str, document_id: str, user_id: str | None = None):
	get_chat_or_404(chat_id)
	if user_id:
		get_user_or_404(user_id)

	processor = PDFProcessor()
	deleted = processor.delete_chat_document(chat_id=chat_id, document_id=document_id, user_id=user_id)
	if not deleted:
		raise HTTPException(status_code=404, detail="Document context not found")

	return {"message": "Document context removed", "document_id": document_id, "chat_id": chat_id}


@router.post("/chats", response_model=ChatSummary)
async def create_chat(payload: ChatCreate):
	chat = db_create_chat(user_id=payload.user_id, title=payload.title or "New chat")
	return ChatSummary(**chat)


@router.get("/users/{user_id}/chats", response_model=list[ChatSummary])
async def list_user_chats(user_id: str):
	chats = db_list_user_chats(user_id)
	return [ChatSummary(**chat) for chat in chats]


@router.get("/chats/{chat_id}", response_model=ChatSummary)
async def get_chat(chat_id: str):
	chat = get_chat_or_404(chat_id)
	return ChatSummary(**chat)


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
	db_delete_chat(chat_id)
	return {"message": "Chat deleted", "chat_id": chat_id}


@router.patch("/chats/{chat_id}", response_model=ChatSummary)
async def update_chat_title(chat_id: str, payload: ChatUpdate):
	updated = db_update_chat_title(chat_id, payload.title)
	if not updated:
		raise HTTPException(status_code=404, detail="Chat not found")
	return ChatSummary(**updated)
