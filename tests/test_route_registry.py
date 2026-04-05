from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


def _route_registry():
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module("lightrag.api.route_registry")
    finally:
        sys.argv = original_argv


def _args() -> SimpleNamespace:
    return SimpleNamespace(
        top_k=5,
        working_dir="workdir",
        input_dir="inputdir",
        llm_binding="openai",
        llm_binding_host="https://llm.example",
        llm_model="gpt-test",
        embedding_binding="openai",
        embedding_binding_host="https://embed.example",
        embedding_model="embed-test",
        summary_max_tokens=256,
        summary_context_size=2048,
        kv_storage="PGKVStorage",
        doc_status_storage="PGDocStatusStorage",
        graph_storage="Neo4JStorage",
        vector_storage="ChromaVectorDBStorage",
        enable_llm_cache_for_extract=True,
        enable_llm_cache=True,
        max_graph_nodes=100,
        rerank_binding="cohere",
        rerank_model="rerank-test",
        rerank_binding_host="https://rerank.example",
        summary_language="English",
        force_llm_summary_on_merge=False,
        max_parallel_insert=4,
        cosine_threshold=0.2,
        min_rerank_score=0.1,
        related_chunk_number=8,
        max_async=4,
        embedding_func_max_async=4,
        embedding_batch_num=8,
    )


def _make_router(prefix: str, suffix: str) -> APIRouter:
    router = APIRouter(prefix=prefix)

    @router.get(suffix)
    async def stub():
        return {"prefix": prefix}

    return router


def _patch_route_builders(monkeypatch):
    route_registry = _route_registry()
    static_mount_calls = []
    monkeypatch.setattr(
        route_registry,
        "create_document_routes",
        lambda rag, doc_manager, api_key: _make_router("/documents", "/stub"),
    )
    monkeypatch.setattr(
        route_registry,
        "create_query_routes",
        lambda rag, api_key, top_k: _make_router("/query", "/stub"),
    )
    monkeypatch.setattr(
        route_registry,
        "create_graph_routes",
        lambda rag, api_key: _make_router("/graph", "/stub"),
    )

    monkeypatch.setattr(
        route_registry,
        "create_ollama_router",
        lambda rag, top_k, api_key: _make_router("", "/version"),
    )
    monkeypatch.setattr(
        route_registry,
        "create_health_router",
        lambda context, combined_auth, auth_handler, version_payload: _make_router(
            "", "/health"
        ),
    )
    monkeypatch.setattr(
        route_registry,
        "get_combined_auth_dependency",
        lambda api_key: (lambda: None),
    )
    monkeypatch.setattr(
        route_registry,
        "register_static_mounts",
        lambda app, webui_assets_exist: static_mount_calls.append(webui_assets_exist),
    )
    return route_registry, static_mount_calls


def _auth_handler(accounts: dict[str, str] | None = None) -> SimpleNamespace:
    accounts = accounts or {}
    return SimpleNamespace(
        accounts=accounts,
        create_token=lambda **kwargs: f"token-for-{kwargs['username']}",
    )


def test_register_app_routes_guest_mode_and_docs_redirect(monkeypatch):
    route_registry, static_mount_calls = _patch_route_builders(monkeypatch)
    auth_handler = _auth_handler()

    app = FastAPI()
    context = route_registry.RouteRegistryContext(
        rag=object(),
        doc_manager=object(),
        api_key=None,
        args=_args(),
        api_version_display="0256",
        webui_assets_exist=False,
        webui_title="LightRAG",
        webui_description="API",
        rerank_enabled=False,
        auth_handler=auth_handler,
    )
    route_registry.register_app_routes(app, context)
    assert static_mount_calls == [False]

    client = TestClient(app)

    root_response = client.get("/", follow_redirects=False)
    assert root_response.status_code == 307
    assert root_response.headers["location"] == "/docs"

    auth_response = client.get("/auth-status")
    assert auth_response.status_code == 200
    assert auth_response.json()["access_token"] == "token-for-guest"
    assert auth_response.json()["auth_mode"] == "disabled"

    login_response = client.post(
        "/login",
        data={"username": "guest", "password": "unused"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"] == "token-for-guest"

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["prefix"] == ""

    webui_response = client.get("/webui", follow_redirects=False)
    assert webui_response.status_code == 307
    assert webui_response.headers["location"] == "/docs"


def test_register_app_routes_mounts_prefixed_routers_and_webui_redirect(monkeypatch):
    route_registry, static_mount_calls = _patch_route_builders(monkeypatch)
    auth_handler = _auth_handler({"alice": "secret"})

    app = FastAPI()
    context = route_registry.RouteRegistryContext(
        rag=object(),
        doc_manager=object(),
        api_key="api-key",
        args=_args(),
        api_version_display="0256",
        webui_assets_exist=True,
        webui_title="LightRAG",
        webui_description="API",
        rerank_enabled=True,
        auth_handler=auth_handler,
    )
    route_registry.register_app_routes(app, context)
    assert static_mount_calls == [True]

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/documents/stub" in paths
    assert "/query/stub" in paths
    assert "/graph/stub" in paths
    assert "/api/version" in paths

    client = TestClient(app)
    root_response = client.get("/", follow_redirects=False)
    assert root_response.status_code == 307
    assert root_response.headers["location"] == "/webui"

    login_response = client.post(
        "/login",
        data={"username": "alice", "password": "secret"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"] == "token-for-alice"
    assert login_response.json()["auth_mode"] == "enabled"
