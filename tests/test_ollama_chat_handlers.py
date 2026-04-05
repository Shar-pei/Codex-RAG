from __future__ import annotations

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace

from fastapi import HTTPException


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_api = _import_router_module("lightrag.api.routers.ollama_api")
ollama_chat_handlers = _import_router_module(
    "lightrag.api.routers.ollama_chat_handlers"
)
ollama_models = _import_router_module("lightrag.api.routers.ollama_models")


def _server_infos():
    return SimpleNamespace(
        LIGHTRAG_MODEL="demo-model",
        LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
    )


def test_ollama_api_reexports_chat_handlers():
    assert ollama_api.execute_chat_request is ollama_chat_handlers.execute_chat_request
    assert (
        ollama_api.iter_chat_stream_payloads
        is ollama_chat_handlers.iter_chat_stream_payloads
    )


def test_execute_chat_request_non_stream_falls_back_for_empty_response():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}
            self.query_calls = []

        async def aquery(self, query, param):
            self.query_calls.append((query, param))
            return ""

    request = ollama_models.OllamaChatRequest(
        model="demo",
        messages=[ollama_models.OllamaMessage(role="user", content="hello")],
        stream=False,
    )
    rag = RagStub()

    response = asyncio.run(
        ollama_chat_handlers.execute_chat_request(
            rag, _server_infos(), request, top_k=5
        )
    )

    assert rag.query_calls[0][0] == "hello"
    assert response["model"] == "demo-model"
    assert response["message"]["content"] == "No response generated"
    assert response["done"] is True


def test_execute_chat_request_stream_string_response_emits_two_lines():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

        async def llm_model_func(
            self, query, stream=False, history_messages=None, **kwargs
        ):
            return "hello world"

    request = ollama_models.OllamaChatRequest(
        model="demo",
        messages=[ollama_models.OllamaMessage(role="user", content="/bypass hello")],
        stream=True,
    )

    response = asyncio.run(
        ollama_chat_handlers.execute_chat_request(
            RagStub(), _server_infos(), request, top_k=5
        )
    )

    async def collect_lines():
        lines = []
        async for chunk in response.body_iterator:
            lines.append(chunk)
        return lines

    lines = asyncio.run(collect_lines())
    payloads = [json.loads(line) for line in lines]

    assert payloads[0]["message"]["content"] == "hello world"
    assert payloads[0]["done"] is False
    assert payloads[1]["done"] is True
    assert payloads[1]["done_reason"] == "stop"


def test_iter_chat_stream_payloads_emits_error_and_final_lines():
    async def broken_stream():
        yield "hello"
        raise ValueError("boom")

    async def collect_lines():
        lines = []
        async for chunk in ollama_chat_handlers.iter_chat_stream_payloads(
            response=broken_stream(),
            server_infos=_server_infos(),
            prompt_tokens=1,
            start_time=0,
        ):
            lines.append(chunk)
        return lines

    payloads = [json.loads(line) for line in asyncio.run(collect_lines())]

    assert payloads[0]["message"]["content"] == "hello"
    assert payloads[1]["error"] == "\n\nError: Provider error: boom"
    assert payloads[2]["done"] is True


def test_execute_chat_request_rejects_non_user_terminal_message():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

    request = ollama_models.OllamaChatRequest(
        model="demo",
        messages=[ollama_models.OllamaMessage(role="assistant", content="hello")],
        stream=False,
    )

    try:
        asyncio.run(
            ollama_chat_handlers.execute_chat_request(
                RagStub(), _server_infos(), request, top_k=5
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Last message must be from user role"
    else:
        raise AssertionError("Expected HTTPException")
