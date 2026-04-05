from __future__ import annotations

import importlib
import sys


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


query_route_docs = _import_router_module("lightrag.api.routers.query_route_docs")


def test_query_routes_reexport_query_route_response_docs():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert query_routes.QUERY_ROUTE_RESPONSES is query_route_docs.QUERY_ROUTE_RESPONSES
    assert (
        query_routes.QUERY_STREAM_ROUTE_RESPONSES
        is query_route_docs.QUERY_STREAM_ROUTE_RESPONSES
    )
    assert (
        query_routes.QUERY_DATA_ROUTE_RESPONSES
        is query_route_docs.QUERY_DATA_ROUTE_RESPONSES
    )


def test_query_route_responses_keep_reference_and_error_examples():
    responses = query_route_docs.QUERY_ROUTE_RESPONSES

    assert "with_chunk_content" in responses[200]["content"]["application/json"][
        "examples"
    ]
    assert responses[500]["content"]["application/json"]["example"]["detail"] == (
        "Failed to process query: LLM service unavailable"
    )


def test_query_stream_route_responses_keep_ndjson_examples():
    responses = query_route_docs.QUERY_STREAM_ROUTE_RESPONSES
    examples = responses[200]["content"]["application/x-ndjson"]["examples"]

    assert "streaming_with_references" in examples
    assert '{"error": "LLM service temporarily unavailable"}' in examples[
        "error_response"
    ]["value"]
    assert responses[500]["content"]["application/json"]["example"]["detail"] == (
        "Failed to process streaming query: Knowledge graph unavailable"
    )


def test_query_data_route_responses_keep_structured_schema_examples():
    responses = query_route_docs.QUERY_DATA_ROUTE_RESPONSES
    schema = responses[200]["content"]["application/json"]["schema"]
    examples = responses[200]["content"]["application/json"]["examples"]

    assert schema["required"] == ["status", "message", "data", "metadata"]
    assert examples["successful_local_mode"]["value"]["data"]["entities"][0][
        "entity_name"
    ] == "Neural Networks"
