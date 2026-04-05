from __future__ import annotations

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


ollama_metadata_endpoints = _import_router_module(
    "lightrag.api.routers.ollama_metadata_endpoints"
)


def _server_infos():
    return SimpleNamespace(
        LIGHTRAG_MODEL="demo-model",
        LIGHTRAG_CREATED_AT="2026-04-05T00:00:00Z",
        LIGHTRAG_SIZE=12345,
        LIGHTRAG_DIGEST="sha256:demo",
        LIGHTRAG_NAME="demo-family",
    )


def test_ollama_api_reexports_metadata_builders():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    assert ollama_api.build_ollama_version_response is (
        ollama_metadata_endpoints.build_ollama_version_response
    )
    assert ollama_api.build_ollama_tags_response is (
        ollama_metadata_endpoints.build_ollama_tags_response
    )
    assert ollama_api.build_ollama_running_models_response is (
        ollama_metadata_endpoints.build_ollama_running_models_response
    )


def test_build_ollama_version_response_returns_fixed_contract():
    response = ollama_metadata_endpoints.build_ollama_version_response()

    assert response.version == "0.9.3"


def test_build_ollama_tags_response_uses_server_infos():
    response = ollama_metadata_endpoints.build_ollama_tags_response(_server_infos())

    assert response.models[0].name == "demo-model"
    assert response.models[0].details.family == "demo-family"
    assert response.models[0].size == 12345


def test_build_ollama_running_models_response_uses_server_infos():
    response = ollama_metadata_endpoints.build_ollama_running_models_response(
        _server_infos()
    )

    assert response.models[0].model == "demo-model"
    assert response.models[0].size_vram == 12345
    assert response.models[0].details.family == "llama"
