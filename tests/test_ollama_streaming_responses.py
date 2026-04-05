from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_chat_handlers = _import_router_module(
    "lightrag.api.routers.ollama_chat_handlers"
)
ollama_generate_handlers = _import_router_module(
    "lightrag.api.routers.ollama_generate_handlers"
)
ollama_models = _import_router_module("lightrag.api.routers.ollama_models")
ollama_streaming_responses = _import_router_module(
    "lightrag.api.routers.ollama_streaming_responses"
)


def test_build_ollama_streaming_response_uses_standard_ndjson_contract():
    async def iterator():
        yield "{}\n"

    response = ollama_streaming_responses.build_ollama_streaming_response(iterator())

    assert response.media_type == "application/x-ndjson"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["x-accel-buffering"] == "no"


def test_execute_generate_request_uses_shared_streaming_wrapper():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

        async def llm_model_func(self, query, stream=False, **kwargs):
            return "hello"

    request = ollama_models.OllamaGenerateRequest(
        model="demo", prompt="hello", stream=True
    )
    original = ollama_generate_handlers.build_ollama_streaming_response
    calls = []

    def fake_build(body_iterator):
        calls.append(body_iterator)
        return "wrapped"

    ollama_generate_handlers.build_ollama_streaming_response = fake_build
    try:
        response = asyncio.run(
            ollama_generate_handlers.execute_generate_request(
                RagStub(),
                SimpleNamespace(
                    LIGHTRAG_MODEL="demo-model",
                    LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
                ),
                request,
            )
        )
    finally:
        ollama_generate_handlers.build_ollama_streaming_response = original

    assert response == "wrapped"
    assert len(calls) == 1


def test_execute_chat_request_uses_shared_streaming_wrapper():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

        async def llm_model_func(
            self, query, stream=False, history_messages=None, **kwargs
        ):
            return "hello"

    request = ollama_models.OllamaChatRequest(
        model="demo",
        messages=[ollama_models.OllamaMessage(role="user", content="/bypass hello")],
        stream=True,
    )
    original = ollama_chat_handlers.build_ollama_streaming_response
    calls = []

    def fake_build(body_iterator):
        calls.append(body_iterator)
        return "wrapped"

    ollama_chat_handlers.build_ollama_streaming_response = fake_build
    try:
        response = asyncio.run(
            ollama_chat_handlers.execute_chat_request(
                RagStub(),
                SimpleNamespace(
                    LIGHTRAG_MODEL="demo-model",
                    LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
                ),
                request,
                top_k=5,
            )
        )
    finally:
        ollama_chat_handlers.build_ollama_streaming_response = original

    assert response == "wrapped"
    assert len(calls) == 1
