import fitz
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class PDFProcessor:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name='Qwen/Qwen3-Embedding-0.6B')
        self.db = Chroma(embedding_function=self.embeddings, collection_name='procurement_guidelines',
            persist_directory='../../.chroma_db')
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
                
                # Add metadata to track where the information originated
                metadata = [{"source": file_name} for _ in chunks]
                self.db.add_texts(texts=chunks, metadatas=metadata)
                print(f"✅ Embedded: {file_name} ({len(chunks)} chunks built)")
            except Exception as e:
                print(f"❌ Critical failure reading {file_name}: {e}")
                
        return True

    def retrieve_from_db(self):
        """retrieve relevant info from the vector database based on the query"""
        retriever = self.db.as_retriever(k=50)

        return retriever