from fastapi import APIRouter, HTTPException
from src.data_logic.doc_processor import PDFProcessor
from src.schema.documents_models import FolderDirectoryRequest

#Instantiating router & document processor
router=APIRouter()
processor=PDFProcessor()

#Chat endpoint
@router.post(path='/import')
async def documents_upload(payload:FolderDirectoryRequest):
    """uploads documents to chroma database"""
    try:
        process_status=processor.process_pdf_to_db(payload.folder_directory)
        if process_status==False:
            raise HTTPException(status_code=400,detail="Documents could not be processed")

    
    except Exception as e:
        raise HTTPException(status_code=500,detail= f"Error:{e}")
