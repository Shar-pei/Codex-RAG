from __future__ import annotations

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace

from fastapi import HTTPException
from starlette.requests import Request


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_api = _import_router_module("lightrag.api.routers.ollama_api")


def _build_request(path: str, body: bytes, content_type: str) -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"content-type", content_type.encode("utf-8"))],
    }
    return Request(scope, receive)


def _route_endpoint(api, path: str):
    for route in api.router.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"Route not found: {path}")


def _rag_stub():
    return SimpleNamespace(
        ollama_server_infos=SimpleNamespace(
            LIGHTRAG_MODEL="demo-model",
            LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
        )
    )


def test_generate_route_preserves_parse_http_exception_status():
    api = ollama_api.OllamaAPI(_rag_stub())
    endpoint = _route_endpoint(api, "/generate")
    request = _build_request("/api/generate", b"{not-json", "application/octet-stream")

    try:
        asyncio.run(endpoint(request))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Invalid JSON in request body"
    else:
        raise AssertionError("Expected HTTPException")


def test_chat_route_preserves_helper_http_exception_status():
    api = ollama_api.OllamaAPI(_rag_stub())
    endpoint = _route_endpoint(api, "/chat")
    request = _build_request(
        "/api/chat",
        json.dumps(
            {
                "model": "demo",
                "messages": [{"role": "assistant", "content": "hello"}],
                "stream": False,
            }
        ).encode("utf-8"),
        "application/json",
    )

    try:
        asyncio.run(endpoint(request))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Last message must be from user role"
    else:
        raise AssertionError("Expected HTTPException")


def test_generate_route_still_maps_unexpected_errors_to_500():
    api = ollama_api.OllamaAPI(_rag_stub())
    endpoint = _route_endpoint(api, "/generate")
    request = _build_request(
        "/api/generate",
        json.dumps({"model": "demo", "prompt": "hello"}).encode("utf-8"),
        "application/json",
    )
    original = ollama_api.execute_generate_request

    async def broken_execute_generate_request(rag, server_infos, request):
        raise RuntimeError("provider exploded")

    ollama_api.execute_generate_request = broken_execute_generate_request
    try:
        try:
            asyncio.run(endpoint(request))
        except HTTPException as exc:
            assert exc.status_code == 500
            assert exc.detail == "provider exploded"
        else:
            raise AssertionError("Expected HTTPException")
    finally:
        ollama_api.execute_generate_request = original
