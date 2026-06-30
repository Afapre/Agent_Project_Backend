from typing import Dict, Any
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import register_embedding_function
from sentence_transformers import SentenceTransformer

@register_embedding_function
class MyEmbeddingFunction(EmbeddingFunction):

    def __init__(self, model):

        self.model = model

    def __call__(self, input: Documents) -> Embeddings:
        # embed the documents somehow
        #embeddings = self.model.encode(input, prompt_name="document", normalize_embeddings=True)
       
        # MiniLM does not need a 'prompt_name'
        embeddings = self.model.encode(input, normalize_embeddings=True)

        #return embeddings
        return embeddings.tolist() 
    

    @staticmethod
    def name() -> str:
        return "my-ef"

    # def get_config(self) -> Dict[str, Any]:
    #     return dict(model=self.model)

    # @staticmethod
    # def build_from_config(config: Dict[str, Any]) -> "EmbeddingFunction":
    #     return MyEmbeddingFunction(config['model'])

    def get_config(self) -> Dict[str, Any]:
        # Return only the model name or path, not the actual model object
        #return {"model_name": "LiquidAI/LFM2.5-Embedding-350M"}
        return {"model_name": "sentence-transformers/all-MiniLM-L6-v2"}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "EmbeddingFunction":
        # Re-initialize the model from the name
        model = SentenceTransformer(config['model_name'])
        return MyEmbeddingFunction(model)