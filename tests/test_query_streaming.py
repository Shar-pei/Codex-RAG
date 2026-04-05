from __future__ import annotations

import asyncio
import importlib
import json
import sys


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


class _AsyncChunkIterator:
    def __init__(self, items, error: Exception | None = None):
        self._items = list(items)
        self._error = error
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index < len(self._items):
            item = self._items[self._index]
            self._index += 1
            return item
        if self._error is not None:
            error = self._error
            self._error = None
            raise error
        raise StopAsyncIteration


async def _collect_payloads(async_iterable):
    payloads = []
    async for item in async_iterable:
        payloads.append(item)
    return payloads


query_streaming = _import_router_module("lightrag.api.routers.query_streaming")


def test_query_routes_reexport_query_streaming_helpers():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert (
        query_routes.iter_query_stream_payloads
        is query_streaming.iter_query_stream_payloads
    )
    assert (
        query_routes.build_query_streaming_response
        is query_streaming.build_query_streaming_response
    )


def test_iter_query_stream_payloads_streams_references_and_non_empty_chunks():
    result = {
        "data": {
            "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
            "chunks": [{"reference_id": "1", "content": "chunk-a"}],
        },
        "llm_response": {
            "is_streaming": True,
            "response_iterator": _AsyncChunkIterator(["alpha", "", "beta"]),
        },
    }

    payloads = asyncio.run(
        _collect_payloads(
            query_streaming.iter_query_stream_payloads(
                result,
                include_references=True,
                include_chunk_content=True,
            )
        )
    )

    decoded = [json.loads(item) for item in payloads]
    assert decoded[0] == {
        "references": [
            {
                "reference_id": "1",
                "file_path": "/docs/a.txt",
                "content": ["chunk-a"],
            }
        ]
    }
    assert decoded[1:] == [{"response": "alpha"}, {"response": "beta"}]


def test_iter_query_stream_payloads_emits_error_line_when_stream_fails():
    result = {
        "data": {"references": []},
        "llm_response": {
            "is_streaming": True,
            "response_iterator": _AsyncChunkIterator(["alpha"], RuntimeError("boom")),
        },
    }

    payloads = asyncio.run(
        _collect_payloads(
            query_streaming.iter_query_stream_payloads(
                result,
                include_references=False,
                include_chunk_content=False,
            )
        )
    )

    decoded = [json.loads(item) for item in payloads]
    assert decoded == [{"response": "alpha"}, {"error": "boom"}]


def test_build_query_streaming_response_uses_non_stream_payload_and_headers():
    response = query_streaming.build_query_streaming_response(
        {
            "data": {
                "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
            },
            "llm_response": {"content": "answer", "is_streaming": False},
        },
        include_references=True,
        include_chunk_content=False,
    )

    payloads = asyncio.run(_collect_payloads(response.body_iterator))

    assert response.media_type == "application/x-ndjson"
    assert response.headers["x-accel-buffering"] == "no"
    assert [json.loads(item) for item in payloads] == [
        {
            "response": "answer",
            "references": [{"reference_id": "1", "file_path": "/docs/a.txt"}],
        }
    ]
