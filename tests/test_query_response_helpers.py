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


query_response_helpers = _import_router_module(
    "lightrag.api.routers.query_response_helpers"
)


def test_query_routes_reexport_response_helpers():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert (
        query_routes.prepare_query_references
        is query_response_helpers.prepare_query_references
    )
    assert (
        query_routes.build_query_response_model
        is query_response_helpers.build_query_response_model
    )
    assert (
        query_routes.build_stream_complete_payload
        is query_response_helpers.build_stream_complete_payload
    )


def test_prepare_query_references_enriches_chunk_content_and_can_disable_references():
    data = {
        "references": [
            {"reference_id": "1", "file_path": "/docs/a.txt"},
            {"reference_id": "2", "file_path": "/docs/b.txt"},
        ],
        "chunks": [
            {"reference_id": "1", "content": "chunk-a1"},
            {"reference_id": "1", "content": "chunk-a2"},
            {"reference_id": "2", "content": "chunk-b1"},
        ],
    }

    enriched = query_response_helpers.prepare_query_references(
        data,
        include_references=True,
        include_chunk_content=True,
    )
    disabled = query_response_helpers.prepare_query_references(
        data,
        include_references=False,
        include_chunk_content=True,
    )

    assert enriched[0]["content"] == ["chunk-a1", "chunk-a2"]
    assert enriched[1]["content"] == ["chunk-b1"]
    assert disabled is None


def test_build_query_response_model_uses_fallback_and_optional_references():
    result = {
        "llm_response": {"content": ""},
        "data": {
            "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
            "chunks": [],
        },
    }

    with_references = query_response_helpers.build_query_response_model(
        result,
        include_references=True,
        include_chunk_content=False,
    )
    without_references = query_response_helpers.build_query_response_model(
        result,
        include_references=False,
        include_chunk_content=False,
    )

    assert with_references.response == "No relevant context found for the query."
    assert [ref.model_dump(exclude_none=True) for ref in with_references.references] == [
        {"reference_id": "1", "file_path": "/docs/a.txt"}
    ]
    assert without_references.references is None


def test_build_stream_complete_payload_adds_references_only_when_present():
    llm_response = {"content": "answer"}

    with_references = query_response_helpers.build_stream_complete_payload(
        llm_response,
        [{"reference_id": "1", "file_path": "/docs/a.txt"}],
    )
    without_references = query_response_helpers.build_stream_complete_payload(
        llm_response,
        None,
    )

    assert with_references == {
        "response": "answer",
        "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
    }
    assert without_references == {"response": "answer"}
