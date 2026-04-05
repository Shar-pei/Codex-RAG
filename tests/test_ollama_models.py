from __future__ import annotations

import importlib
import sys


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


ollama_models = _import_router_module("lightrag.api.routers.ollama_models")


def test_ollama_api_reexports_ollama_models():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    assert ollama_api.SearchMode is ollama_models.SearchMode
    assert ollama_api.OllamaMessage is ollama_models.OllamaMessage
    assert ollama_api.OllamaChatRequest is ollama_models.OllamaChatRequest
    assert ollama_api.OllamaChatResponse is ollama_models.OllamaChatResponse
    assert ollama_api.OllamaGenerateRequest is ollama_models.OllamaGenerateRequest
    assert ollama_api.OllamaGenerateResponse is ollama_models.OllamaGenerateResponse
    assert ollama_api.OllamaVersionResponse is ollama_models.OllamaVersionResponse
    assert ollama_api.OllamaModelDetails is ollama_models.OllamaModelDetails
    assert ollama_api.OllamaModel is ollama_models.OllamaModel
    assert ollama_api.OllamaTagResponse is ollama_models.OllamaTagResponse
    assert ollama_api.OllamaRunningModelDetails is (
        ollama_models.OllamaRunningModelDetails
    )
    assert ollama_api.OllamaRunningModel is ollama_models.OllamaRunningModel
    assert ollama_api.OllamaPsResponse is ollama_models.OllamaPsResponse


def test_parse_query_mode_keeps_search_mode_contract():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    cleaned_query, mode, only_need_context, user_prompt = ollama_api.parse_query_mode(
        "/local[use mermaid format] explain graph traversal"
    )

    assert cleaned_query == "explain graph traversal"
    assert mode is ollama_models.SearchMode.local
    assert only_need_context is False
    assert user_prompt == "use mermaid format"


def test_parse_query_mode_keeps_context_prefix_behavior():
    ollama_api = _import_router_module("lightrag.api.routers.ollama_api")

    cleaned_query, mode, only_need_context, user_prompt = ollama_api.parse_query_mode(
        "/mixcontext retrieve context only"
    )

    assert cleaned_query == "retrieve context only"
    assert mode is ollama_models.SearchMode.mix
    assert only_need_context is True
    assert user_prompt is None
