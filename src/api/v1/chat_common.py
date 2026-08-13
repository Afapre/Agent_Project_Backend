import io
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage

from src.addons.text_to_speech import text_to_speech
from src.core.agent_logic import get_clara_agent
from src.data_logic.doc_processor import PDFProcessor
from src.data_logic.postgres import get_chat as db_get_chat
from src.data_logic.postgres import get_user as db_get_user
from src.data_logic.postgres import list_messages as db_list_messages
from src.tools.tools_definition import get_tools

load_dotenv()

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


def get_user_or_404(user_id: str) -> dict:
    user = db_get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_chat_or_404(chat_id: str) -> dict:
    chat = db_get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def build_formatted_history(history: list[dict] | None = None, chat_id: str | None = None) -> list:
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


def compact_context_text(text: str, max_chars: int = MAX_CONTEXT_TEXT_CHARS) -> str:
    cleaned_text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - len("\n\n[... truncated ...]\n\n")
    tail_chars = max(tail_chars, 0)
    return (
        f"{cleaned_text[:head_chars].rstrip()}\n\n[... truncated ...]\n\n{cleaned_text[-tail_chars:].lstrip()}"
        if tail_chars
        else cleaned_text[:max_chars]
    )


def compact_prompt_payload(prompt: str, context_text: str | None = None) -> str:
    final_prompt = prompt.strip()
    if context_text and context_text.strip():
        compact_context = compact_context_text(context_text)
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
            compact_context = compact_context_text(context_text or "", max_chars=allowed_context)
            return (
                "Use the following uploaded document context to answer the user's question.\n\n"
                f"DOCUMENT CONTEXT:\n{compact_context}\n\n"
                f"USER QUESTION:\n{question_part.strip()}"
            )

    return final_prompt[:MAX_COMBINED_PROMPT_CHARS]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text_from_image(file_bytes: bytes) -> str:
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


def validate_document_upload(filename: str, content_type: str | None, content: bytes) -> str:
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


async def extract_document_text(file: UploadFile) -> str:
    filename = (file.filename or "").lower()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    ext = validate_document_upload(filename, file.content_type, content)

    try:
        if ext == ".pdf":
            return extract_text_from_pdf(content)
        if ext == ".docx":
            return extract_text_from_docx(content)
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            return extract_text_from_image(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract text from file: {exc}") from exc

    raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF, DOCX, PNG, JPG, JPEG, or WEBP.")


async def run_clara_agent(
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

    formatted_history = build_formatted_history(history=history, chat_id=chat_id)
    final_prompt = compact_prompt_payload(prompt, context_text)
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
