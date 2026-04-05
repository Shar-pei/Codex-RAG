from __future__ import annotations

import importlib
import sys

import pytest


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


query_models = _import_router_module("lightrag.api.routers.query_models")


def test_query_routes_reexport_extracted_query_models():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert query_routes.QueryRequest is query_models.QueryRequest
    assert query_routes.QueryResponse is query_models.QueryResponse
    assert query_routes.QueryDataResponse is query_models.QueryDataResponse
    assert query_routes.StreamChunkResponse is query_models.StreamChunkResponse


def test_query_request_strips_query_and_validates_conversation_roles():
    request = query_models.QueryRequest(
        query="  explain rag  ",
        conversation_history=[{"role": " user ", "content": "hi"}],
    )

    assert request.query == "explain rag"

    with pytest.raises(ValueError, match="role"):
        query_models.QueryRequest(
            query="hello world",
            conversation_history=[{"content": "missing role"}],
        )


def test_query_request_to_query_params_excludes_api_only_fields_and_sets_stream():
    request = query_models.QueryRequest(
        query="what is ai",
        mode="hybrid",
        include_chunk_content=True,
        top_k=5,
    )

    params = request.to_query_params(is_stream=False)

    assert params.mode == "hybrid"
    assert params.top_k == 5
    assert params.stream is False
    assert not hasattr(params, "include_chunk_content")


def test_query_request_keeps_reference_defaults():
    request = query_models.QueryRequest(query="what is rag")

    assert request.include_references is True
    assert request.include_chunk_content is False
