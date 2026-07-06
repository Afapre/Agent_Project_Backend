import gc
import os
import uuid

import chromadb
import fitz
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
        self._collection = None
        self._llama_client = None

    def _get_llama_client(self):
        if self._llama_client is None:
            try:
                from llama_cloud import LlamaCloud
            except Exception:
                return None

            api_key = os.getenv("LLAMA_CLOUD_API_KEY")
            if not api_key:
                return None

            self._llama_client = LlamaCloud(api_key=api_key)
        return self._llama_client

    @property
    def collection(self):
        self._ensure_loaded()
        return self._collection

    def _extract_text(self, file_path: str) -> str:
        client = self._get_llama_client()
        if client:
            try:
                file_obj = client.files.create(file=file_path, purpose="parse")
                result = client.parsing.parse(
                    file_id=file_obj.id,
                    tier="agentic",
                    version="latest",
                    expand=["markdown"],
                )
                markdown_text = getattr(result, "markdown", None)
                if markdown_text is not None:
                    pages = getattr(markdown_text, "pages", []) or []
                    if pages:
                        combined = []
                        for page in pages:
                            md = getattr(page, "markdown", None)
                            if md:
                                combined.append(md)
                        if combined:
                            return "\n\n".join(combined)
            except Exception as exc:
                print(f"LlamaParse failed for {file_path}: {exc}")

        doc = fitz.open(file_path)
        text = " ".join(page.get_text() for page in doc)
        doc.close()
        return text

    def _ensure_loaded(self):
        if self.embedding is None:
            self.embedding = MyEmbeddingFunction(model=None)
            
        if self.model is None and not getattr(self.embedding, "_use_gemini", False):
            self.model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
            )
            self.embedding.model = self.model

        if self._collection is None:
            provider = "gemini" if getattr(self.embedding, "_use_gemini", False) else "local"
            collection_name = f"procurement_guidelines_v2_{provider}"
            self._collection = client.get_or_create_collection(
                name=collection_name,
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
                text = self._extract_text(file_path)
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