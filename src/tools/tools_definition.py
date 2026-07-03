from langchain.tools import tool
from tavily import TavilyClient


def get_tools(collection, tavily_key):
    tavily_client = TavilyClient(api_key=tavily_key)

    @tool
    def websearch(query: str):
        """Searches the web for information."""
        return tavily_client.search(query)
    
    # def retriever_tool(query: str):
    #     """Searches document database and returns top ranked matches with query"""
    #     # 1. Retrieve initial candidate documents
    #     #documents = retriever(query=query)
    #     documents = retriever.invoke(query)
    #     # Most retrievers return a list of Document objects, so we extract the .page_content
    #     doc_texts = [doc.page_content for doc in documents]
        
    #     # 2. Prepare pairs for the CrossEncoder
    #     pairs = [(query, text) for text in doc_texts]
        
    #     # 3. Get relevance scores
    #     scores = model.predict(pairs)
        
    #     # 4. Pair documents with their scores and sort by score descending
    #     ranked_docs = sorted(zip(doc_texts, scores), key=lambda x: x[1], reverse=True)
        
    #     # 5. Return the documents in their new ranked order
    #     return [doc for doc, score in ranked_docs][:2]
    

    def retriever_tool(query: str):
        """Searches document database and returns top ranked matches with query"""

        # 1. Search ChromaDB
        results = collection.query(query_texts=[query], n_results=50)
        doc_texts = results['documents'][0]

        if not doc_texts:
            return "No relevant documents found."

        # Reranking is disabled to keep memory usage low on free-tier deployments.
        return doc_texts[:3]


    # doc_tool = create_retriever_tool(
    #     retriever, 
    #     "pdf_document_search", 
    #     "Searches document database and returns top ranked matches with query."
    # )

    return [websearch,retriever_tool]

