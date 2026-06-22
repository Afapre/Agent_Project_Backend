from fastapi import APIRouter
from src.api.v1.documents import router as documents_router
from src.api.v1.chat import router as chat_router

general_router=APIRouter(prefix='/api/v1')

#Adding documents and chat routers to general router
general_router.include_router(documents_router,prefix='/documents', tags=["Documents Management"])
general_router.include_router(chat_router, prefix='/chat', tags=["Chat Engine"])