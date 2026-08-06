import gc
import os
import uuid
import chromadb
import fitz
from dotenv import load_dotenv, find_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from src.data_logic.embedding import MyEmbeddingFunction
from PIL import Image
import io
import boto3
from fastapi.staticfiles import StaticFiles
from chromadb.errors import ChromaError



load_dotenv(find_dotenv())

ENV = os.getenv("ENV", "development")
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
API_KEY=os.getenv("CHROMA_API_KEY")
TENANT=os.getenv("CHROMA_TENANT")
DATABASE=os.getenv("CHROMA_DATABASE")

try:
    client = chromadb.CloudClient(
        api_key=API_KEY,
        tenant=TENANT,
        database=DATABASE,
    )
    client.heartbeat()
    print("Successful connection to Chroma Cloud.")

except Exception as e:
    print(f"Warning: Could not connect to Chroma Cloud. Error: {e}")



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
    
    def _extract_image(self,file_path):
        #Opening document for extracting image
        doc = fitz.open(file_path)
        img_list=[]
        #Looping through every page in a document
        for page_index in range(len(doc)):
            page = doc[page_index]
            #extracting full images from each document page
            image_list = page.get_images(full=True)
            
            #looping through the different images found on a page
            for img_index, img in enumerate(image_list):
                #getting the unique id of image
                xref = img[0]
                #getting actual image content using it's unique id
                base_image = doc.extract_image(xref)
                #getting the binary data(0s & 1s) making up image
                image_bytes = base_image["image"]
                #getting file type of image eg JPEG
                image_ext = base_image["ext"]
                
                # --- STRATEGIC FORMAT CONVERSION & VALIDITY CHECK START ---
                try:
                    # Converts the raw image bytes into an in-memory file stream 
                    # so the PIL library can read it without saving it to disk first.
                    image_stream = io.BytesIO(image_bytes)
                    
                    with Image.open(image_stream) as pil_img:
                        # Verify if the image is too small (often noise, icons, or vector lines)
                        if pil_img.width < 50 or pil_img.height < 50:
                            continue 
                            
                        # Convert transparent (RGBA), palette (P), or print (CMYK) images 
                        # to standard RGB so they can be saved cleanly as a standard JPEG.
                        if pil_img.mode in ("RGBA", "LA", "P", "CMYK"):
                            pil_img = pil_img.convert("RGB")
                        
                        # Create a new in-memory file container for our standardized image
                        output_stream = io.BytesIO()
                        
                        # Re-encode the image strictly into a clean, universally accepted JPEG format
                        pil_img.save(output_stream, format="JPEG", quality=95)
                        
                        # Overwrite the original bytes with our pristine, newly generated JPEG bytes
                        image_bytes = output_stream.getvalue()
                        
                        # Hardcode the extension label to match our Gemini pipeline expectations
                        image_ext = "jpeg"
                    
                    # Adding binary data representation of each extracted image together with its file ext type to img_list
                    img_list.append((image_bytes, image_ext))
                    
                except Exception as e:
                    print(f"⚠️ Skipping invalid image at page {page_index}, index {img_index}: {e}")
                    continue
                # --- STRATEGIC FORMAT CONVERSION & VALIDITY CHECK END ---

                # Adding binary data representation of each extracted image together with its file ext type to img_list
                #img_list.append((image_bytes,image_ext))
        doc.close()
        return img_list


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

    # def process_pdf_to_db(self, target_directory):
    #     """Discovers, parses, and injects all PDFs within the target folder into Chroma."""
    #     self._ensure_loaded()

    #     pdf_files = [f for f in os.listdir(target_directory) if f.lower().endswith(".pdf")]

    #     if not pdf_files:
    #         print(f"⚠️ No PDF documents discovered in folder: '{target_directory}'")
    #         return False

    #     splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=400,
    #         chunk_overlap=40,
    #         separators=["\n\n", "\n", " ", ""],
    #     )

    #     for file_name in pdf_files:
    #         file_path = os.path.join(target_directory, file_name)
    #         try:
    #             text = self._extract_text(file_path)
    #             images=self._extract_image(file_path)
    #             chunks = splitter.split_text(text)

    #             ids = [str(uuid.uuid4()) for _ in chunks]
    #             img_ids=[str(uuid.uuid4()) for _ in images]

    #             # 1. Embed and Add Text
    #             self.collection.add(documents=chunks, ids=ids)
    #             print(f"📥 Text chunks added to collection for {file_name}.")
    #             #print(f"✅ Embedded: {file_name} ({len(chunks)} chunks built)")


    #             # 2. Embed and Add Images
    #             #self.collection.add(documents=images, ids=img_ids)
    #             if images:
    #                 # Since 'images' is not a standard Chroma field for embedding functions 
    #                 # to trigger via __call__, we pass the result of the embedding function directly:
    #                 img_embeddings = self.embedding(images=images) # Calls the __call__ dispatcher from the embedding file
                    
    #                 self.collection.add(
    #                     documents=[f"img_{file_name}_{i}" for i in range(len(images))],# Dummy docs
    #                     embeddings=img_embeddings,# We pass the vectors gotten above
    #                     ids=img_ids
    #                 )
    #                 print(f"📥 {len(images)} image embeddings added to collection for {file_name}.")
    #             else:
    #                 print(f"ℹ️ No images found in {file_name}.")
                
    #         except Exception as e:
    #             print(f"❌ Critical failure reading {file_name}: {e}")
    #         finally:
    #             gc.collect()

    #     return True

    def process_pdf_to_db(self, target_path):
        """Discovers, parses, and injects PDFs from either a folder directory or a single file into Chroma."""
        self._ensure_loaded()
        
        pdf_files = []
        
        # Check if input path is a directory or a file
        if os.path.isdir(target_path):
            pdf_files = [os.path.join(target_path, f) for f in os.listdir(target_path) if f.lower().endswith(".pdf")]
            if not pdf_files:
                print(f"⚠️ No PDF documents discovered in folder: '{target_path}'")
                return False
        elif os.path.isfile(target_path):
            if target_path.lower().endswith(".pdf"):
                pdf_files = [target_path]
            else:
                print(f"⚠️ Provided file is not a PDF: '{target_path}'")
                return False
        else:
            print(f"⚠️ Path is neither a valid directory nor a file: '{target_path}'")
            return False

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=40,
            separators=["\n\n", "\n", " ", ""],
        )

        for file_path in pdf_files:
            file_name = os.path.basename(file_path)
            try:
                text = self._extract_text(file_path)
                images = self._extract_image(file_path)
                chunks = splitter.split_text(text)

                ids = [str(uuid.uuid4()) for _ in chunks]
                img_ids = [str(uuid.uuid4()) for _ in images]

                # 1. Embed and Add Text
                self.collection.add(documents=chunks, ids=ids)
                print(f"📥 Text chunks added to collection for {file_name}.")

                # 2. Embed and Add Images
                # if images:
                #     img_embeddings = self.embedding.embed_images(images)

                #     self.collection.add(
                #         documents=[f"img_{file_name}_{i}" for i in range(len(images))],
                #         embeddings=img_embeddings,
                #         ids=img_ids
                #     )
                #     print(f"📥 {len(images)} image embeddings added to collection for {file_name}.")
                # else:
                #     print(f"ℹ️ No images found in {file_name}.")

                if images:
                    img_embeddings = self.embedding.embed_images(images)
                    img_metadatas = []

                    for i, (img_bytes, ext) in enumerate(images):
                        unique_filename = f"{uuid.uuid4()}.{ext}"
                        
                        if ENV == "production":
                            s3_client = boto3.client('s3')
                            s3_key = f"extracted_images/{unique_filename}"
                            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=img_bytes, ContentType=f"image/{ext}")
                            url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                        else:
                            os.makedirs("static/extracted_images", exist_ok=True)
                            with open(f"static/extracted_images/{unique_filename}", "wb") as f:
                                f.write(img_bytes)
                            url = f"/static/extracted_images/{unique_filename}"
                        
                        img_metadatas.append({"image_url": url})

                    self.collection.add(
                        documents=[f"img_{file_name}_{i}" for i in range(len(images))],
                        embeddings=img_embeddings,
                        ids=[str(uuid.uuid4()) for _ in images],
                        metadatas=img_metadatas
                    )
                    print(f"📥 {len(images)} image embeddings added to collection for {file_name}.")
                else:
                    print(f"ℹ️ No images found in {file_name}.")
                
            except Exception as e:
                print(f"❌ Critical failure reading {file_name}: {e}")
                #Re-raise the exception so the route function can catch it
                raise e
            finally:
                gc.collect()

        return True