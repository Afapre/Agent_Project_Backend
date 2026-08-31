from __future__ import annotations

from typing import Any


def _normalize_document_ids(document_ids: list[str] | None) -> list[str]:
    return [doc_id for doc_id in (document_ids or []) if doc_id]


def build_scope_wheres(
    *,
    user_id: str | None = None,
    chat_id: str | None = None,
    document_ids: list[str] | None = None,
    include_user_knowledge: bool = True,
) -> list[dict[str, Any] | None]:
    normalized_ids = _normalize_document_ids(document_ids)
    if normalized_ids:
        if len(normalized_ids) == 1:
            return [{"document_id": normalized_ids[0]}]
        return [{"document_id": {"$in": normalized_ids}}]

    wheres: list[dict[str, Any] | None] = []

    if user_id and chat_id:
        wheres.append({"$and": [{"user_id": user_id}, {"chat_id": chat_id}]})
        if include_user_knowledge:
            wheres.append({"$and": [{"user_id": user_id}, {"source_type": "knowledge"}]})
        return wheres

    if user_id:
        wheres.append({"user_id": user_id})
        return wheres

    if chat_id:
        wheres.append({"chat_id": chat_id})
        return wheres

    return [None]


def query_scope_matches(
    collection,
    query_text: str,
    *,
    user_id: str | None = None,
    chat_id: str | None = None,
    document_ids: list[str] | None = None,
    n_results: int = 5,
    include_user_knowledge: bool = True,
) -> list[tuple[str, dict[str, Any]]]:
    wheres = build_scope_wheres(
        user_id=user_id,
        chat_id=chat_id,
        document_ids=document_ids,
        include_user_knowledge=include_user_knowledge,
    )

    formatted_matches: list[tuple[str, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()

    for where in wheres:
        query_args: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "metadatas"],
        }
        if where is not None:
            query_args["where"] = where

        results = collection.query(**query_args)
        documents = results.get("documents", [[]])[0] or []
        metadatas = results.get("metadatas", [[]])[0] or []

        for document, metadata in zip(documents, metadatas):
            metadata = metadata or {}
            filename = str(metadata.get("filename") or "Uploaded file")
            fingerprint = (filename, str(document))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            formatted_matches.append((str(document), metadata))

    return formatted_matches