from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from src.data_logic.doc_processor import PDFProcessor
from src.schema.documents_models import FolderDirectoryRequest
from src.schema.documents_models import FileRequest
from src.api.v1.chat_common import extract_document_text
import os
from typing import List
import shutil
import uuid

#Instantiating router & document processor
router=APIRouter()
processor=PDFProcessor()

#Chat endpoint
@router.post(path='/import')
async def documents_upload(payload: FolderDirectoryRequest):
    """Uploads documents from a folder directory to the chroma database"""
    try:
        # Normalize path to safely clear JSON escape character issues
        folder_path = os.path.normpath(payload.folder_directory)
        process_status = processor.process_pdf_to_db(folder_path)
        
        if process_status == False:
            raise HTTPException(status_code=400, detail="Folder documents could not be processed")
        return {"message": "Folder processed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    

@router.post(path='/upload')
async def upload_multiple_documents(files: List[UploadFile] = File(...)):
    results = {"success": [], "errors": []}
    
    for file in files:
        temp_path = f"temp_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Assuming process_pdf_to_db now returns True/False or raises an exception
            # We wrap the call to catch specific issues
            processor.process_pdf_to_db(temp_path)
            results["success"].append(file.filename)
            
        except Exception as e:
            results["errors"].append({"file": file.filename, "error": str(e)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return results # Postman will now see exactly which files failed and why


@router.post(path='/upload-knowledge')
async def upload_knowledge_files(
    files: List[UploadFile] = File(...),
    user_id: str = Form(...),
    related_document_id: str | None = Form(default=None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded")

    results = {"success": [], "errors": []}

    for file in files:
        try:
            extracted_text = await extract_document_text(file)
            if not extracted_text.strip():
                raise HTTPException(status_code=422, detail="No readable text could be extracted from the uploaded file")

            processor = PDFProcessor()
            document_id = str(uuid.uuid4())
            chunk_count = processor.index_document_text(
                extracted_text,
                document_id=document_id,
                filename=file.filename or "uploaded-file",
                user_id=user_id,
                chat_id=None,
                source_type="knowledge",
                related_document_id=related_document_id or None,
            )

            if chunk_count == 0:
                raise HTTPException(status_code=422, detail="The uploaded file did not produce any retrievable content")

            results["success"].append({
                "id": document_id,
                "filename": file.filename or "uploaded-file",
                "chunk_count": chunk_count,
                "related_document_id": related_document_id or None,
            })
        except Exception as e:
            results["errors"].append({"file": file.filename, "error": str(e)})

    return results


@router.get(path='/knowledge')
async def list_knowledge_documents(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="User id is required")

    return processor.list_user_knowledge_documents(user_id=user_id)


@router.delete(path='/knowledge/{document_id}')
async def delete_knowledge_document(document_id: str, user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="User id is required")

    deleted = processor.delete_user_knowledge_document(user_id=user_id, document_id=document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found")

    return {"message": "Knowledge document removed", "document_id": document_id}


# @router.post(path='/upload')
# async def single_document_upload(payload: FileRequest):
#     """Uploads a single document path to the chroma database"""
#     try:
#         # Normalize path for single file
#         file_path = os.path.normpath(payload.file_path)
#         process_status = processor.process_pdf_to_db(file_path)
        
#         if process_status == False:
#             raise HTTPException(status_code=400, detail="Single document could not be processed")
#         return {"message": "File processed successfully"}
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {e}")


# @router.post(path='/upload')
# async def upload_multiple_documents(files: List[UploadFile] = File(...)):
#     """
#     Uploads one or more documents to the chroma database.
#     """
#     try:
#         results = []
#         for file in files:
#             # 1. Save the uploaded file to a temporary location
#             # (FastAPI stores UploadFiles in memory or temp disk)
#             temp_file_path = f"temp_{file.filename}"
#             with open(temp_file_path, "wb") as buffer:
#                 shutil.copyfileobj(file.file, buffer)
            
#             # 2. Process the file using your existing logic
#             success = processor.process_pdf_to_db(temp_file_path)
            
#             # 3. Cleanup temp file
#             if os.path.exists(temp_file_path):
#                 os.remove(temp_file_path)
                
#             if not success:
#                 raise HTTPException(status_code=400, detail=f"Failed to process {file.filename}")
            
#             results.append(file.filename)
            
#         return {"message": "Files processed successfully", "files": results}
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {e}")