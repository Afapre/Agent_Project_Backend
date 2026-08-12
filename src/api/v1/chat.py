import io
import os
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
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
    update_chat_title as db_update_chat_title,
)
from src.exceptions.harmful_exceptions import HarmfulContentError
from src.schema.chat_models import (
    ChatCreate,
    ChatRequest,
    ChatResponse,
    ChatResult,
    ChatSummary,
    MessageCreate,
    MessageFeedbackUpdate,
    MessageResponse,
    UserCreate,
    UserLoginRequest,
    UserResponse,
    ChatUpdate,
)
from src.tools.tools_definition import get_tools

load_dotenv()

router = APIRouter()

MAX_CONTEXT_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_CONTEXT_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_CONTEXT_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/webp",
}
MAX_CONTEXT_TEXT_CHARS = 14000
MAX_COMBINED_PROMPT_CHARS = 22000


def _normalize_user_name(payload: UserCreate) -> tuple[str, str] | None:
    if payload.first_name is not None or payload.last_name is not None:
        first_name = (payload.first_name or "").strip()
        last_name = (payload.last_name or "").strip()
        return first_name, last_name

    full_name = (payload.name or "").strip()
    if not full_name:
        return None

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
    formatted_history: list[Any] = []

    if chat_id:
        for message in db_list_messages(chat_id):
            role = str(message.get("role", "")).lower()
            content = message.get("content", "")
            if role == "user":
                formatted_history.append(HumanMessage(content=str(content)))
            elif role == "assistant":
                formatted_history.append(AIMessage(content=str(content)))

    if history:
        for msg in history:
            role = str(msg.get("role", "")).lower()
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(HumanMessage(content=str(content)))
            elif role == "assistant":
                formatted_history.append(AIMessage(content=str(content)))

    return formatted_history


def _compact_context_text(text: str, max_chars: int = MAX_CONTEXT_TEXT_CHARS) -> str:
    cleaned_text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - len("\n\n[... truncated ...]\n\n")
    tail_chars = max(tail_chars, 0)
    return f"{cleaned_text[:head_chars].rstrip()}\n\n[... truncated ...]\n\n{cleaned_text[-tail_chars:].lstrip()}" if tail_chars else cleaned_text[:max_chars]


def _compact_prompt_payload(prompt: str, context_text: str | None = None) -> str:
    final_prompt = prompt.strip()
    if context_text and context_text.strip():
        compact_context = _compact_context_text(context_text)
        final_prompt = (
            "Use the following uploaded document context to answer the user's question.\n\n"
            f"DOCUMENT CONTEXT:\n{compact_context}\n\n"
            f"USER QUESTION:\n{final_prompt}"
        )

    if len(final_prompt) <= MAX_COMBINED_PROMPT_CHARS:
        return final_prompt

    if "USER QUESTION:" in final_prompt and "DOCUMENT CONTEXT:" in final_prompt:
        prefix, question_part = final_prompt.rsplit("USER QUESTION:", 1)
        if len(question_part.strip()) < MAX_COMBINED_PROMPT_CHARS // 3:
            return final_prompt[:MAX_COMBINED_PROMPT_CHARS]

        allowed_context = MAX_COMBINED_PROMPT_CHARS - len(question_part) - len("USER QUESTION:") - 200
        if allowed_context > 0:
            compact_context = _compact_context_text(context_text or "", max_chars=allowed_context)
            return (
                "Use the following uploaded document context to answer the user's question.\n\n"
                f"DOCUMENT CONTEXT:\n{compact_context}\n\n"
                f"USER QUESTION:\n{question_part.strip()}"
            )

    return final_prompt[:MAX_COMBINED_PROMPT_CHARS]


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_text_from_image(file_bytes: bytes) -> str:
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        import pytesseract
    except ImportError as exc:
        raise HTTPException(
            status_code=400,
            detail="OCR dependencies are not installed. Please install pillow and pytesseract for image uploads.",
        ) from exc

    image = Image.open(io.BytesIO(file_bytes))
    if image.mode not in {"L", "RGB"}:
        image = image.convert("RGB")

    # Upscale + contrast sharpening makes small screenshots and table text much more OCR-friendly.
    width, height = image.size
    scale_factor = 2.0 if min(width, height) > 700 else 3.0
    upscaled = image.resize((int(width * scale_factor), int(height * scale_factor)), Image.Resampling.LANCZOS)

    grayscale = ImageOps.grayscale(upscaled)
    contrasted = ImageEnhance.Contrast(grayscale).enhance(2.0)
    sharpened = contrasted.filter(ImageFilter.SHARPEN)

    binary = sharpened.point(lambda p: 255 if p > 170 else 0)

    candidates = [
        (upscaled, "--oem 3 --psm 6"),
        (sharpened, "--oem 3 --psm 6"),
        (binary, "--oem 3 --psm 6"),
        (binary, "--oem 3 --psm 11"),
    ]

    extracted_texts: list[str] = []
    for candidate_image, config in candidates:
        text = pytesseract.image_to_string(candidate_image, config=config).strip()
        if text:
            extracted_texts.append(text)

    if not extracted_texts:
        return ""

    # Prefer the richest OCR result and append meaningful extra lines from alternates.
    best = max(extracted_texts, key=len)
    best_lines = {line.strip() for line in best.splitlines() if line.strip()}
    merged_lines = [line for line in best.splitlines() if line.strip()]

    for variant in extracted_texts:
        if variant == best:
            continue
        for line in variant.splitlines():
            normalized_line = line.strip()
            if normalized_line and normalized_line not in best_lines:
                best_lines.add(normalized_line)
                merged_lines.append(normalized_line)

    return "\n".join(merged_lines).strip()


def _validate_document_upload(filename: str, content_type: str | None, content: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]

    if ext not in SUPPORTED_CONTEXT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload PDF, DOCX, PNG, JPG, JPEG, or WEBP.",
        )

    normalized_content_type = (content_type or "").lower().strip()
    if normalized_content_type and normalized_content_type not in SUPPORTED_CONTEXT_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file content type. Upload a PDF, DOCX, or supported image file.",
        )

    if len(content) > MAX_CONTEXT_UPLOAD_SIZE_BYTES:
        max_size_mb = MAX_CONTEXT_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum upload size is {max_size_mb} MB.",
        )

    return ext


async def _extract_document_text(file: UploadFile) -> str:
    filename = (file.filename or "").lower()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    ext = _validate_document_upload(filename, file.content_type, content)

    try:
        if ext == ".pdf":
            return _extract_text_from_pdf(content)
        if ext == ".docx":
            return _extract_text_from_docx(content)
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            return _extract_text_from_image(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract text from file: {exc}") from exc

    raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF, DOCX, PNG, JPG, JPEG, or WEBP.")


async def _run_clara_agent(
    prompt: str,
    history: list[dict] | None = None,
    chat_id: str | None = None,
    context_text: str | None = None,
    user_id: str | None = None,
    document_ids: list[str] | None = None,
) -> tuple[str, str | None]:
    google_key = os.getenv("GOOGLE_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not google_key:
        raise HTTPException(status_code=500, detail="Missing GOOGLE_API_KEY environment variable.")

    processor = PDFProcessor()
    collection = processor.collection
    tools = get_tools(
        collection,
        tavily_key,
        user_id=user_id,
        chat_id=chat_id,
        document_ids=document_ids,
    )
    agent = get_clara_agent(tools, google_key)

    formatted_history = _build_formatted_history(history=history, chat_id=chat_id)

    final_prompt = _compact_prompt_payload(prompt, context_text)

    formatted_history.append(HumanMessage(content=final_prompt))

    response = agent.invoke({"messages": formatted_history})

    if isinstance(response, dict) and "messages" in response:
        message_list = response["messages"]
        ai_msg = None
        for msg in reversed(message_list):
            if hasattr(msg, "type") and getattr(msg, "type", "") == "ai":
                ai_msg = msg
                break
        raw_content = ai_msg.content if ai_msg else message_list[-1].content
    else:
        raw_content = response.content if hasattr(response, "content") else response

    final_text = ""
    if isinstance(raw_content, list):
        for item in raw_content:
            if isinstance(item, dict):
                if "text" in item:
                    final_text += str(item["text"])
                elif "content" in item:
                    final_text += str(item["content"])
            else:
                final_text += str(item)
    else:
        final_text = str(raw_content).strip()

    audio_base64 = text_to_speech(final_text)
    return final_text.strip(), audio_base64 if audio_base64 else None


@router.post("/documents/upload-context")
async def upload_document_context(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    chat_id: str | None = Form(default=None),
):
    if user_id:
        _get_user(user_id)
    if chat_id:
        _get_chat(chat_id)

    extracted_text = await _extract_document_text(file)
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
    _get_chat(chat_id)
    if user_id:
        _get_user(user_id)

    processor = PDFProcessor()
    return processor.list_chat_documents(chat_id=chat_id, user_id=user_id)


@router.delete("/chats/{chat_id}/documents/{document_id}")
async def delete_chat_document(chat_id: str, document_id: str, user_id: str | None = None):
    _get_chat(chat_id)
    if user_id:
        _get_user(user_id)

    processor = PDFProcessor()
    deleted = processor.delete_chat_document(chat_id=chat_id, document_id=document_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document context not found")

    return {"message": "Document context removed", "document_id": document_id, "chat_id": chat_id}


@router.post(path="/message", response_model=ChatResult)
async def chat_with_clara(payload: ChatRequest):
    try:
        user = _get_user(payload.user_id)
        chat = _get_chat(payload.chat_id) if payload.chat_id else None

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

        final_text, audio_base64 = await _run_clara_agent(
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
        )
    except HarmfulContentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/users", response_model=UserResponse)
async def create_user(payload: UserCreate):
    try:
        created = db_create_user(
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
            email=payload.email,
            password=payload.password,
            date_of_birth=payload.date_of_birth,
        )
        return UserResponse(**created)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/users/login", response_model=UserResponse)
async def login_user(payload: UserLoginRequest):
    try:
        user = db_login_user(email=payload.email, password=payload.password)
        return UserResponse(**user)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    user = _get_user(user_id)
    return UserResponse(**user)


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
    chat = _get_chat(chat_id)
    return ChatSummary(**chat)


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    db_delete_chat(chat_id)
    return {"message": "Chat deleted", "chat_id": chat_id}


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


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    db_delete_user(user_id)
    return {"message": "User deleted", "user_id": user_id}


@router.patch("/chats/{chat_id}", response_model=ChatSummary)
async def update_chat_title(chat_id: str, payload: ChatUpdate):
    updated = db_update_chat_title(chat_id, payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatSummary(**updated)