from __future__ import annotations

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_generate_handlers = _import_router_module(
    "lightrag.api.routers.ollama_generate_handlers"
)
ollama_models = _import_router_module("lightrag.api.routers.ollama_models")


def _server_infos():
    return SimpleNamespace(
        LIGHTRAG_MODEL="demo-model",
        LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
    )


def test_ollama_api_reexports_generate_handlers():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    assert ollama_api.execute_generate_request is (
        ollama_generate_handlers.execute_generate_request
    )
    assert ollama_api.iter_generate_stream_payloads is (
        ollama_generate_handlers.iter_generate_stream_payloads
    )


def test_execute_generate_request_non_stream_falls_back_for_empty_response():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

        async def llm_model_func(self, query, stream=False, **kwargs):
            return ""

    request = ollama_models.OllamaGenerateRequest(model="demo", prompt="hello")

    response = asyncio.run(
        ollama_generate_handlers.execute_generate_request(
            RagStub(), _server_infos(), request
        )
    )

    assert response["model"] == "demo-model"
    assert response["response"] == "No response generated"
    assert response["done"] is True


def test_execute_generate_request_stream_string_response_emits_two_lines():
    class RagStub:
        def __init__(self):
            self.llm_model_kwargs = {}

        async def llm_model_func(self, query, stream=False, **kwargs):
            return "hello world"

    request = ollama_models.OllamaGenerateRequest(
        model="demo", prompt="hello", stream=True
    )

    response = asyncio.run(
        ollama_generate_handlers.execute_generate_request(
            RagStub(), _server_infos(), request
        )
    )

    async def collect_lines():
        lines = []
        async for chunk in response.body_iterator:
            lines.append(chunk)
        return lines

    lines = asyncio.run(collect_lines())
    payloads = [json.loads(line) for line in lines]

    assert payloads[0]["response"] == "hello world"
    assert payloads[0]["done"] is False
    assert payloads[1]["done"] is True
    assert payloads[1]["done_reason"] == "stop"
