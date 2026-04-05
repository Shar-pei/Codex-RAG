from __future__ import annotations

import asyncio
import importlib
import json
import sys

from fastapi import HTTPException
from starlette.requests import Request


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_models = _import_router_module("lightrag.api.routers.ollama_models")
ollama_request_helpers = _import_router_module(
    "lightrag.api.routers.ollama_request_helpers"
)


def _build_request(body: bytes, content_type: str) -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/chat",
        "headers": [(b"content-type", content_type.encode("utf-8"))],
    }
    return Request(scope, receive)


def test_ollama_api_reexports_request_helpers():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    assert ollama_api.parse_request_body is ollama_request_helpers.parse_request_body
    assert ollama_api.estimate_tokens is ollama_request_helpers.estimate_tokens
    assert ollama_api.parse_query_mode is ollama_request_helpers.parse_query_mode


def test_parse_request_body_supports_octet_stream_json():
    request = _build_request(
        json.dumps({"model": "demo", "prompt": "hello"}).encode("utf-8"),
        "application/octet-stream",
    )

    parsed = asyncio.run(
        ollama_request_helpers.parse_request_body(
            request, ollama_models.OllamaGenerateRequest
        )
    )

    assert parsed.model == "demo"
    assert parsed.prompt == "hello"


def test_parse_request_body_rejects_invalid_json():
    request = _build_request(b"{not-json", "application/octet-stream")

    try:
        asyncio.run(
            ollama_request_helpers.parse_request_body(
                request, ollama_models.OllamaGenerateRequest
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "Invalid JSON in request body"
    else:
        raise AssertionError("Expected HTTPException")


def test_parse_query_mode_keeps_extracted_search_mode_contract():
    cleaned_query, mode, only_need_context, user_prompt = (
        ollama_request_helpers.parse_query_mode(
            "/local[use mermaid format] explain graph traversal"
        )
    )

    assert cleaned_query == "explain graph traversal"
    assert mode is ollama_models.SearchMode.local
    assert only_need_context is False
    assert user_prompt == "use mermaid format"
