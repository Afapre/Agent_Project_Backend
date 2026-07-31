import os
from typing import Any, Dict
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import register_embedding_function
from sentence_transformers import SentenceTransformer
from google.genai import types


@register_embedding_function
class MyEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model=None):
        self.model = model
        self._gemini_client = None
        self._use_gemini = os.getenv("USE_GEMINI_EMBEDDINGS", "true").lower() in {"1", "true", "yes", "on"}

    def _get_gemini_client(self):
        if self._gemini_client is None and self._use_gemini:
            try:
                from google import genai
            except Exception:
                self._use_gemini = False
                return None

            self._gemini_client = genai.Client()
        return self._gemini_client

    def _embed_with_gemini(self, input_content: Documents, is_text: bool = True) -> list[list[float]]:
        client = self._get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client unavailable")

        embeddings = []
        if is_text:
            for text in input_content:
                result = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=text,
                )
                embedding = getattr(result, "embeddings", None)
                if embedding and len(embedding) > 0:
                    values = getattr(embedding[0], "values", None)
                    if values is not None:
                        embeddings.append(list(values))
                    else:
                        embeddings.append([])
                else:
                    embeddings.append([])
        else:
            for img_bytes, img_ext in input_content:
                mime_type = f"image/{img_ext}" if not str(img_ext).startswith("image/") else img_ext
                result = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=[
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                )
                embedding = getattr(result, "embeddings", None)
                if embedding and len(embedding) > 0:
                    values = getattr(embedding[0], "values", None)
                    if values is not None:
                        embeddings.append(list(values))
                    else:
                        embeddings.append([])
                else:
                    embeddings.append([])
        return embeddings

    def embed_images(self, images: list[tuple[bytes, str]]) -> list[list[float]]:
        if not images:
            return []
        return self._embed_with_gemini(images, is_text=False)

    def __call__(self, input: Documents) -> Embeddings:
        # 1. Validation: Ensure we have something to embed
        if input is None:
            raise TypeError("Embedding input cannot be None")

        # 2. Attempt Gemini Embedding (Primary Route)
        if self._use_gemini and self._get_gemini_client() is not None:
            try:
                # Detect if input is a batch of images (list of tuples) or standard text (list of strings)
                is_image_batch = isinstance(input, list) and bool(input) and isinstance(input[0], tuple)
                if is_image_batch:
                    # Route to specialized image embedding logic
                    return self.embed_images(input)
                # Route to general text embedding logic
                return self._embed_with_gemini(input, is_text=True)
            except Exception as exc:
                print(f"Gemini embedding failed, falling back to SentenceTransformer: {exc}")
        
        # 3. Handle Fallback / Error Scenarios
        # If Gemini failed, ensure we don't try to send images to a text-only local model
        if isinstance(input, list) and bool(input) and isinstance(input[0], tuple):
            raise RuntimeError("Gemini failed and no fallback model available for image embeddings.")

        # 4. Local Fallback (SentenceTransformer)
        # Initialize the local model if it hasn't been loaded yet
        if self.model is None:
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")

        # Perform embedding locally using the CPU
        embeddings = self.model.encode(input, batch_size=8, normalize_embeddings=True)
        return embeddings.tolist()


    @staticmethod
    def name() -> str:
        return "my-ef"

    def get_config(self) -> Dict[str, Any]:
        return {"model_name": "gemini-embedding-001"}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "EmbeddingFunction":
        model = SentenceTransformer(config["model_name"])
        return MyEmbeddingFunction(model)