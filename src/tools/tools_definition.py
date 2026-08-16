from langchain.tools import tool
from tavily import TavilyClient
from src.data_logic.retrieval_scope import query_scope_matches
from src.tools.procurement_tools import create_procurement_tools


def get_tools(
    collection,
    tavily_key,
    user_id=None,
    chat_id=None,
    document_ids=None,
    audit_callback=None,
):
    tavily_client = TavilyClient(api_key=tavily_key)

    @tool
    def websearch(query: str):
        """Searches the web for current market prices, vendor information, and industry benchmarks."""
        return tavily_client.search(query)

    @tool
    def retriever_tool(query: str):
        """Searches the current chat context and the user's shared knowledge base.

        Results are tagged with their source document (and, when applicable, the
        master document an amendment relates to) so answers can carry inline
        citations and reconcile a master agreement with its amendments.
        Use for past RFPs, awarded contracts, procurement policies, and supplier agreements.
        """

        matches = query_scope_matches(
            collection,
            query,
            user_id=user_id,
            chat_id=chat_id,
            document_ids=document_ids,
            n_results=8,
            include_user_knowledge=True,
        )

        if not matches:
            return "No relevant documents found."

        formatted_matches = []
        distinct_filenames: set[str] = set()
        for doc, meta in matches[:6]:
            meta = meta or {}
            filename = str(meta.get("filename") or "Uploaded file")
            distinct_filenames.add(filename)

            header = f"Document: {filename}"
            if meta.get("related_document_filename"):
                header += f" (Amendment to: {meta['related_document_filename']})"

            match_str = f"{header}\nText: {doc}"
            if meta.get("image_url"):
                match_str += f"\nImage Reference URL: {meta['image_url']}"

            formatted_matches.append(match_str)

        result = "\n\n---\n\n".join(formatted_matches)

        if len(distinct_filenames) > 1:
            filenames_list = ", ".join(sorted(distinct_filenames))
            result += (
                f"\n\n[Note: These matches span {len(distinct_filenames)} distinct documents: "
                f"{filenames_list}. If the user's request refers ambiguously to one of them "
                "(e.g. a supplier or deal name that matches more than one contract), ask the "
                "user to clarify which document they mean instead of guessing.]"
            )

        return result

    procurement_tools = create_procurement_tools(
        collection=collection,
        user_id=user_id,
        chat_id=chat_id,
        audit_callback=audit_callback,
    )

    return [websearch, retriever_tool, *procurement_tools]
