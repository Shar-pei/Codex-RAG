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


ollama_chat_handlers = _import_router_module(
    "lightrag.api.routers.ollama_chat_handlers"
)
ollama_generate_handlers = _import_router_module(
    "lightrag.api.routers.ollama_generate_handlers"
)
ollama_stream_payloads = _import_router_module(
    "lightrag.api.routers.ollama_stream_payloads"
)


def _server_infos():
    return SimpleNamespace(
        LIGHTRAG_MODEL="demo-model",
        LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
    )


def test_build_generate_chunk_payload_keeps_shared_non_terminal_shape():
    payload = ollama_stream_payloads.build_generate_chunk_payload(
        _server_infos(), "hello"
    )

    assert payload == {
        "model": "demo-model",
        "created_at": "2026-04-05T00:00:00Z",
        "response": "hello",
        "done": False,
    }


def test_build_chat_chunk_payload_keeps_shared_non_terminal_shape():
    payload = ollama_stream_payloads.build_chat_chunk_payload(_server_infos(), "hello")

    assert payload == {
        "model": "demo-model",
        "created_at": "2026-04-05T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": "hello",
            "images": None,
        },
        "done": False,
    }


def test_build_generate_done_payload_keeps_shared_metrics_contract():
    payload = ollama_stream_payloads.build_generate_done_payload(
        server_infos=_server_infos(),
        total_response="hello world",
        prompt_tokens=3,
        start_time=10,
        first_chunk_time=14,
        last_chunk_time=24,
    )

    assert payload["model"] == "demo-model"
    assert payload["response"] == ""
    assert payload["done"] is True
    assert payload["done_reason"] == "stop"
    assert payload["total_duration"] == 14
    assert payload["prompt_eval_duration"] == 4


def test_build_chat_error_payload_keeps_terminal_error_shape():
    error_payload, final_payload = ollama_stream_payloads.build_chat_error_payload(
        _server_infos(), "Provider error: boom"
    )

    assert error_payload["message"]["content"] == "\n\nError: Provider error: boom"
    assert error_payload["error"] == "\n\nError: Provider error: boom"
    assert error_payload["done"] is False
    assert final_payload["message"]["content"] == ""
    assert final_payload["done"] is True


def test_iter_generate_stream_payloads_uses_shared_chunk_builder_for_string_response():
    async def collect_lines():
        lines = []
        async for line in ollama_generate_handlers.iter_generate_stream_payloads(
            response="hello world",
            server_infos=_server_infos(),
            prompt_tokens=1,
            start_time=0,
        ):
            lines.append(line)
        return lines

    original = ollama_generate_handlers.build_generate_chunk_payload
    calls = []

    def fake_build(server_infos, content):
        calls.append((server_infos, content))
        return {
            "model": "demo-model",
            "created_at": "2026-04-05T00:00:00Z",
            "response": "patched",
            "done": False,
        }

    ollama_generate_handlers.build_generate_chunk_payload = fake_build
    try:
        lines = asyncio.run(collect_lines())
    finally:
        ollama_generate_handlers.build_generate_chunk_payload = original

    assert len(calls) == 1
    assert calls[0][1] == "hello world"
    assert json.loads(lines[0])["response"] == "patched"


def test_iter_generate_stream_payloads_uses_shared_done_builder():
    async def collect_lines():
        lines = []
        async for line in ollama_generate_handlers.iter_generate_stream_payloads(
            response="hello world",
            server_infos=_server_infos(),
            prompt_tokens=1,
            start_time=0,
        ):
            lines.append(line)
        return lines

    original = ollama_generate_handlers.build_generate_done_payload
    calls = []

    def fake_build(**kwargs):
        calls.append(kwargs)
        return {"model": "demo-model", "response": "", "done": True, "done_reason": "stop"}

    ollama_generate_handlers.build_generate_done_payload = fake_build
    try:
        lines = asyncio.run(collect_lines())
    finally:
        ollama_generate_handlers.build_generate_done_payload = original

    assert len(calls) == 1
    assert json.loads(lines[1])["done"] is True


def test_iter_chat_stream_payloads_uses_shared_chunk_builder_for_async_chunks():
    async def chunk_stream():
        yield "hello"
        yield ""
        yield " world"

    async def collect_lines():
        lines = []
        async for line in ollama_chat_handlers.iter_chat_stream_payloads(
            response=chunk_stream(),
            server_infos=_server_infos(),
            prompt_tokens=1,
            start_time=0,
        ):
            lines.append(line)
        return lines

    original = ollama_chat_handlers.build_chat_chunk_payload
    calls = []

    def fake_build(server_infos, content):
        calls.append((server_infos, content))
        return {
            "model": "demo-model",
            "created_at": "2026-04-05T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": content.upper(),
                "images": None,
            },
            "done": False,
        }

    ollama_chat_handlers.build_chat_chunk_payload = fake_build
    try:
        lines = asyncio.run(collect_lines())
    finally:
        ollama_chat_handlers.build_chat_chunk_payload = original

    assert [content for _, content in calls] == ["hello", " world"]
    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["message"]["content"] == "HELLO"
    assert payloads[1]["message"]["content"] == " WORLD"


def test_iter_chat_stream_payloads_uses_shared_error_builder():
    async def broken_stream():
        yield "hello"
        raise ValueError("boom")

    async def collect_lines():
        lines = []
        async for line in ollama_chat_handlers.iter_chat_stream_payloads(
            response=broken_stream(),
            server_infos=_server_infos(),
            prompt_tokens=1,
            start_time=0,
        ):
            lines.append(line)
        return lines

    original = ollama_chat_handlers.build_chat_error_payload
    calls = []

    def fake_build(server_infos, error_msg):
        calls.append((server_infos, error_msg))
        return (
            {
                "model": "demo-model",
                "message": {"role": "assistant", "content": "\n\nError: test", "images": None},
                "error": "\n\nError: test",
                "done": False,
            },
            {
                "model": "demo-model",
                "message": {"role": "assistant", "content": "", "images": None},
                "done": True,
            },
        )

    ollama_chat_handlers.build_chat_error_payload = fake_build
    try:
        lines = asyncio.run(collect_lines())
    finally:
        ollama_chat_handlers.build_chat_error_payload = original

    assert len(calls) == 1
    payloads = [json.loads(line) for line in lines]
    assert payloads[1]["error"] == "\n\nError: test"
    assert payloads[2]["done"] is True
