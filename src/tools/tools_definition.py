from langchain.tools import tool
from tavily import TavilyClient
from src.data_logic.retrieval_scope import query_scope_matches


def get_tools(collection, tavily_key, user_id=None, chat_id=None, document_ids=None):
    tavily_client = TavilyClient(api_key=tavily_key)

    @tool
    def websearch(query: str):
        """Searches the web for information."""
        return tavily_client.search(query)
    

    # def retriever_tool(query: str):
    #     """Searches document database and returns top ranked matches with query"""

    #     # 1. Search ChromaDB
    #     results = collection.query(query_texts=[query], n_results=50)
    #     doc_texts = results['documents'][0]

    #     if not doc_texts:
    #         return "No relevant documents found."

    #     # Reranking is disabled to keep memory usage low on free-tier deployments.
    #     return doc_texts[:3]

    def retriever_tool(query: str):
        """Searches the current chat context and the user's shared knowledge base."""

        matches = query_scope_matches(
            collection,
            query,
            user_id=user_id,
            chat_id=chat_id,
            document_ids=document_ids,
            n_results=5,
            include_user_knowledge=True,
        )

        if not matches:
            return "No relevant documents found."

        formatted_matches = []
        for doc, meta in matches:
            match_str = f"Text: {doc}"
            if meta and meta.get("image_url"):
                match_str += f"\nImage Reference URL: {meta['image_url']}"
                
            formatted_matches.append(match_str)

        return "\n\n---\n\n".join(formatted_matches[:3])


    # doc_tool = create_retriever_tool(
    #     retriever, 
    #     "pdf_document_search", 
    #     "Searches document database and returns top ranked matches with query."
    # )

    return [websearch,retriever_tool]

