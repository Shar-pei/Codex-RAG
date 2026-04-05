from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _import_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


app_health_routes = _import_module("lightrag.api.app_health_routes")


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        webui_assets_exist=True,
        rerank_enabled=True,
        args=SimpleNamespace(
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
        ),
    )


def _auth_handler(accounts: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(accounts=accounts or {})


def _version_payload() -> dict[str, str]:
    return {
        "core_version": "1.0.0",
        "api_version": "2.0.0",
        "webui_title": "LightRAG",
        "webui_description": "API",
    }


def test_create_health_router_returns_a_fresh_router_each_time():
    router_one = app_health_routes.create_health_router(
        _context(),
        combined_auth=lambda: None,
        auth_handler=_auth_handler(),
        version_payload=_version_payload(),
    )
    router_two = app_health_routes.create_health_router(
        _context(),
        combined_auth=lambda: None,
        auth_handler=_auth_handler(),
        version_payload=_version_payload(),
    )

    assert router_one is not router_two
    assert [route.path for route in router_one.routes] == ["/health"]
    assert [route.path for route in router_two.routes] == ["/health"]


def test_health_router_uses_header_workspace_and_builds_expected_payload(monkeypatch):
    calls = []

    monkeypatch.setattr(app_health_routes, "get_default_workspace", lambda: "workspace-a")
    monkeypatch.setattr(app_health_routes, "cleanup_keyed_lock", lambda: {"count": 0})

    async def fake_namespace_data(namespace: str, workspace: str | None = None):
        calls.append((namespace, workspace))
        return {"busy": True}

    monkeypatch.setattr(app_health_routes, "get_namespace_data", fake_namespace_data)

    app = FastAPI()
    app.include_router(
        app_health_routes.create_health_router(
            _context(),
            combined_auth=lambda: None,
            auth_handler=_auth_handler(),
            version_payload=_version_payload(),
        )
    )

    client = TestClient(app)
    response = client.get("/health", headers={"LIGHTRAG-WORKSPACE": " tenant-a "})

    assert response.status_code == 200
    payload = response.json()
    assert calls == [("pipeline_status", "tenant-a")]
    assert payload["pipeline_busy"] is True
    assert payload["auth_mode"] == "disabled"
    assert payload["keyed_locks"] == {"count": 0}
    assert payload["configuration"]["workspace"] == "workspace-a"


def test_health_router_maps_unexpected_errors_to_500(monkeypatch):
    monkeypatch.setattr(app_health_routes, "get_default_workspace", lambda: "workspace-a")

    async def broken_namespace_data(namespace: str, workspace: str | None = None):
        raise RuntimeError("backend exploded")

    monkeypatch.setattr(app_health_routes, "get_namespace_data", broken_namespace_data)

    app = FastAPI()
    app.include_router(
        app_health_routes.create_health_router(
            _context(),
            combined_auth=lambda: None,
            auth_handler=_auth_handler({"alice": "secret"}),
            version_payload=_version_payload(),
        )
    )

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 500
    assert response.json()["detail"] == "backend exploded"
