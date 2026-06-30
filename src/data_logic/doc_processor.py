import fitz
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import uuid
from sentence_transformers import SentenceTransformer
from src.data_logic.embedding import MyEmbeddingFunction
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())

client = chromadb.CloudClient(
  api_key=os.getenv('CHROMA_API_KEY'),
  tenant=os.getenv('CHROMA_TENANT'),
  database=os.getenv('CHROMA_DATABASE')
)
class PDFProcessor:
    def __init__(self):
        # default_ef = DefaultEmbeddingFunction()
        # embeddings = default_ef(["foo"])
        #self.model=SentenceTransformer("LiquidAI/LFM2.5-Embedding-350M",trust_remote_code=True,)
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.embedding=MyEmbeddingFunction(self.model)
        self.collection = client.get_or_create_collection(name="procurement_guidelines_v2",embedding_function=self.embedding )
        
       #embedding_function=OpenAIEmbeddingFunction(model_name="text-embedding-3-small")

        #self.embeddings = HuggingFaceEmbeddings(model_name='Qwen/Qwen3-Embedding-0.6B')
        #self.db = Chroma(embedding_function=self.embeddings, collection_name='procurement_guidelines',persist_directory='../../.chroma_db')
        #self.target_directory = target_directory
        #os.makedirs(self.target_directory, exist_ok=True)
    
    def process_pdf_to_db(self,target_directory):
        """Discovers, parses, and injects all PDFs within the target folder into Chroma."""
        pdf_files = [f for f in os.listdir(target_directory) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"⚠️ No PDF documents discovered in folder: '{target_directory}'")
            return False
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,  # Optimized smaller chunk sizes reduce RAG token cost expansion
            chunk_overlap=60,
            separators=["\n\n", "\n", " ", ""]
        )
        
        for file_name in pdf_files:
            file_path = os.path.join(target_directory, file_name)
            try:
                doc = fitz.open(file_path)
                # Keep case sensitivity and formatting so semantic search matches accurately
                text = " ".join([page.get_text() for page in doc])
                
                # Split raw strings directly into vector chunks
                chunks = splitter.split_text(text)
                # DEBUG: Test a single chunk encoding
                try:
                    test_embedding = self.model.encode(chunks[0])
                    print("DEBUG: Embedding successful for test chunk")
                except Exception as e:
                    print(f"DEBUG: Model encoding failed: {e}")
                
                # Add metadata to track where the information originated
                #metadata = [{"source": file_name} for _ in chunks]
                #self.db.add_texts(texts=chunks, metadatas=metadata)

                ids = [str(uuid.uuid4()) for _ in chunks]
                
                self.collection.add(documents=chunks, ids=ids)
                print(f"✅ Embedded: {file_name} ({len(chunks)} chunks built)")
            except Exception as e:
                print(f"❌ Critical failure reading {file_name}: {e}")
                
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