from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

from fastapi import APIRouter


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_api = _import_router_module("lightrag.api.routers.ollama_api")


def _rag_stub():
    return SimpleNamespace(
        ollama_server_infos=SimpleNamespace(
            LIGHTRAG_MODEL="demo-model",
            LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
        )
    )


def test_create_ollama_router_returns_a_fresh_router_each_time():
    router_one = ollama_api.create_ollama_router(_rag_stub(), top_k=5, api_key="k1")
    router_two = ollama_api.create_ollama_router(_rag_stub(), top_k=5, api_key="k1")

    assert router_one is not router_two
    assert [route.path for route in router_one.routes] == [
        "/version",
        "/tags",
        "/ps",
        "/generate",
        "/chat",
    ]
    assert [route.path for route in router_two.routes] == [
        "/version",
        "/tags",
        "/ps",
        "/generate",
        "/chat",
    ]


def test_ollama_api_preserves_router_compatibility_surface(monkeypatch):
    sentinel_router = APIRouter()
    calls = []
    original = ollama_api.create_ollama_router

    def fake_create_ollama_router(rag, top_k=60, api_key=None):
        calls.append((rag, top_k, api_key))
        return sentinel_router

    monkeypatch.setattr(ollama_api, "create_ollama_router", fake_create_ollama_router)
    try:
        api = ollama_api.OllamaAPI(_rag_stub(), top_k=7, api_key="secret")
    finally:
        monkeypatch.setattr(ollama_api, "create_ollama_router", original)

    assert calls and calls[0][1:] == (7, "secret")
    assert api.router is sentinel_router
