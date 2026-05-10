import fitz
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document

def process_pdf_to_db(pdf_path):
    # PDF Cleaning Logic
    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc]).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # RAG Setup
    embeddings = HuggingFaceEmbeddings(model_name='Qwen/Qwen3-Embedding-0.6B')
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    segments = splitter.split_documents([Document(page_content=text)])
    
    db = Chroma(embedding_function=embeddings, collection_name='procurement_guidelines')
    db.add_documents(segments)
    return db.as_retriever()