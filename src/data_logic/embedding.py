import os
from typing import Any, Dict

from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import register_embedding_function
from sentence_transformers import SentenceTransformer


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

    def _embed_with_gemini(self, input_texts: Documents) -> list[list[float]]:
        client = self._get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client unavailable")

        embeddings = []
        for text in input_texts:
            result = client.models.embed_content(
                model="gemini-embedding-001",
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
        return embeddings

    def __call__(self, input: Documents) -> Embeddings:
        if self._use_gemini and self._get_gemini_client() is not None:
            try:
                return self._embed_with_gemini(input)
            except Exception as exc:
                print(f"Gemini embedding failed, falling back to SentenceTransformer: {exc}")

        if self.model is None:
            self.model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
            )

        embeddings = self.model.encode(
            input,
            batch_size=8,
            normalize_embeddings=True,
        )
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