from langchain_core.tools import create_retriever_tool
from langchain.tools import tool
from tavily import TavilyClient

def get_tools(retriever, tavily_key):
    tavily_client = TavilyClient(api_key=tavily_key)

    @tool
    def websearch(query: str):
        """Searches the web for information."""
        return tavily_client.search(query)

    doc_tool = create_retriever_tool(
        retriever, 
        "pdf_document_search", 
        "Search procurement guidelines."
    )
    
    return [websearch, doc_tool]