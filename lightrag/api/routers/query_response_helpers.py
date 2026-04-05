from __future__ import annotations

from typing import Any, Optional

from lightrag.api.routers.query_models import QueryResponse


def prepare_query_references(
    data: dict[str, Any],
    include_references: bool,
    include_chunk_content: bool,
) -> list[dict[str, Any]] | None:
    """Normalize query references and optionally enrich them with chunk content."""
    if not include_references:
        return None

    references = data.get("references", [])
    if not include_chunk_content:
        return references

    chunks = data.get("chunks", [])
    ref_id_to_content: dict[str, list[str]] = {}
    for chunk in chunks:
        ref_id = chunk.get("reference_id", "")
        content = chunk.get("content", "")
        if ref_id and content:
            ref_id_to_content.setdefault(ref_id, []).append(content)

    enriched_references = []
    for ref in references:
        ref_copy = ref.copy()
        ref_id = ref.get("reference_id", "")
        if ref_id in ref_id_to_content:
            ref_copy["content"] = ref_id_to_content[ref_id]
        enriched_references.append(ref_copy)
    return enriched_references


def get_query_response_content(llm_response: dict[str, Any]) -> str:
    """Return the non-streaming query response content with fallback text."""
    response_content = llm_response.get("content", "")
    if not response_content:
        return "No relevant context found for the query."
    return response_content


def build_query_response_model(
    result: dict[str, Any],
    include_references: bool,
    include_chunk_content: bool,
) -> QueryResponse:
    """Build the /query response model from a unified aquery_llm result."""
    llm_response = result.get("llm_response", {})
    data = result.get("data", {})
    references = prepare_query_references(
        data,
        include_references=include_references,
        include_chunk_content=include_chunk_content,
    )
    return QueryResponse(
        response=get_query_response_content(llm_response),
        references=references,
    )


def build_stream_complete_payload(
    llm_response: dict[str, Any],
    references: Optional[list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build the single-message payload used when /query/stream falls back to non-streaming output."""
    payload = {"response": get_query_response_content(llm_response)}
    if references is not None:
        payload["references"] = references
    return payload
