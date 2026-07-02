import gc
import os
import uuid

import fitz
import chromadb
from dotenv import load_dotenv, find_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from src.data_logic.embedding import MyEmbeddingFunction

load_dotenv(find_dotenv())

client = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE"),
)


class PDFProcessor:
    def __init__(self):
        self.model = None
        self.embedding = None
        self.collection = None

    def _ensure_loaded(self):
        if self.model is None:
            self.model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
            )
            self.embedding = MyEmbeddingFunction(self.model)
            self.collection = client.get_or_create_collection(
                name="procurement_guidelines_v2",
                embedding_function=self.embedding,
            )
        return self.model

    def process_pdf_to_db(self, target_directory):
        """Discovers, parses, and injects all PDFs within the target folder into Chroma."""
        self._ensure_loaded()

        pdf_files = [f for f in os.listdir(target_directory) if f.lower().endswith(".pdf")]

        if not pdf_files:
            print(f"⚠️ No PDF documents discovered in folder: '{target_directory}'")
            return False

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=40,
            separators=["\n\n", "\n", " ", ""],
        )

        for file_name in pdf_files:
            file_path = os.path.join(target_directory, file_name)
            try:
                doc = fitz.open(file_path)
                text = " ".join(page.get_text() for page in doc)
                doc.close()

                chunks = splitter.split_text(text)

                ids = [str(uuid.uuid4()) for _ in chunks]
                self.collection.add(documents=chunks, ids=ids)
                print(f"✅ Embedded: {file_name} ({len(chunks)} chunks built)")
            except Exception as e:
                print(f"❌ Critical failure reading {file_name}: {e}")
            finally:
                gc.collect()

        return True

    # def retrieve_from_db(self):
    #     """retrieve relevant info from the vector database based on the query"""
    #     #retriever = self.db.as_retriever(k=50)
    #     retriever = self.collection.query(n_results=50)

    #     return retriever

    # In src/data_logic/doc_processor.py

    # def retrieve_from_db(self, query: str):
    #     """retrieve relevant info from the vector database based on the query"""
    #     # Pass the query string here!
    #     results = self.collection.query(
    #         query_texts=[query], 
    #         n_results=50
    #     )
    #     return results