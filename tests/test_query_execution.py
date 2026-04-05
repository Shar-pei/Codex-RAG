from __future__ import annotations

import asyncio
import importlib
import sys


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


class _RecordingRag:
    def __init__(self, llm_result=None, data_result=None):
        self.llm_result = llm_result
        self.data_result = data_result
        self.calls = []

    async def aquery_llm(self, query, param):
        self.calls.append(("aquery_llm", query, param))
        return self.llm_result

    async def aquery_data(self, query, param):
        self.calls.append(("aquery_data", query, param))
        return self.data_result


query_execution = _import_router_module("lightrag.api.routers.query_execution")
query_models = _import_router_module("lightrag.api.routers.query_models")


def test_query_routes_reexport_query_execution_helpers():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert query_routes.build_query_text_param is query_execution.build_query_text_param
    assert query_routes.build_query_data_param is query_execution.build_query_data_param
    assert (
        query_routes.execute_query_text_request
        is query_execution.execute_query_text_request
    )
    assert (
        query_routes.execute_query_data_request
        is query_execution.execute_query_data_request
    )
    assert (
        query_routes.normalize_query_data_response
        is query_execution.normalize_query_data_response
    )


def test_build_query_text_param_forces_stream_false():
    request = query_models.QueryRequest(query="what is rag", stream=True, top_k=5)

    param = query_execution.build_query_text_param(request)

    assert param.stream is False
    assert param.top_k == 5


def test_execute_query_text_request_uses_non_stream_query_and_formats_response():
    request = query_models.QueryRequest(
        query="what is rag",
        include_references=True,
        include_chunk_content=True,
    )
    rag = _RecordingRag(
        llm_result={
            "llm_response": {"content": "answer"},
            "data": {
                "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
                "chunks": [{"reference_id": "1", "content": "chunk-a"}],
            },
        }
    )

    response = asyncio.run(query_execution.execute_query_text_request(rag, request))

    assert rag.calls[0][0] == "aquery_llm"
    assert rag.calls[0][2].stream is False
    assert response.response == "answer"
    assert [ref.model_dump(exclude_none=True) for ref in response.references] == [
        {
            "reference_id": "1",
            "file_path": "/docs/a.txt",
            "content": ["chunk-a"],
        }
    ]


def test_normalize_query_data_response_handles_dict_and_invalid_response():
    valid = query_execution.normalize_query_data_response(
        {
            "status": "success",
            "message": "ok",
            "data": {"entities": []},
            "metadata": {"query_mode": "mix"},
        }
    )
    invalid = query_execution.normalize_query_data_response("unexpected")

    assert valid.status == "success"
    assert valid.metadata == {"query_mode": "mix"}
    assert invalid.status == "failure"
    assert invalid.message == "Invalid response type"
    assert invalid.data == {}
    assert invalid.metadata == {}


def test_execute_query_data_request_uses_non_stream_param_and_normalizes():
    request = query_models.QueryRequest(query="what is rag", stream=True)
    rag = _RecordingRag(
        data_result={
            "status": "success",
            "message": "ok",
            "data": {"references": []},
            "metadata": {"query_mode": "mix"},
        }
    )

    response = asyncio.run(query_execution.execute_query_data_request(rag, request))

    assert rag.calls[0][0] == "aquery_data"
    assert rag.calls[0][2].stream is False
    assert response.status == "success"
    assert response.metadata == {"query_mode": "mix"}
