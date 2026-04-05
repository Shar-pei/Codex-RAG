from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


def _import_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


app_route_context = _import_module("lightrag.api.app_route_context")
route_registry = _import_module("lightrag.api.route_registry")


def _context(auth_handler=None):
    return app_route_context.RouteRegistryContext(
        rag=object(),
        doc_manager=object(),
        api_key="api-key",
        args=SimpleNamespace(top_k=5),
        api_version_display="0256",
        webui_assets_exist=True,
        webui_title="LightRAG",
        webui_description="API",
        rerank_enabled=False,
        auth_handler=auth_handler,
    )


def test_build_version_payload_keeps_route_registry_metadata_contract():
    payload = app_route_context.build_version_payload(_context())

    assert payload["api_version"] == "0256"
    assert payload["webui_title"] == "LightRAG"
    assert payload["webui_description"] == "API"
    assert payload["core_version"]


def test_resolve_auth_handler_prefers_context_override():
    override = object()

    assert app_route_context.resolve_auth_handler(_context(auth_handler=override)) is override


def test_resolve_auth_handler_falls_back_to_lazy_auth_module(monkeypatch):
    fake_auth_handler = object()
    fake_module = SimpleNamespace(auth_handler=fake_auth_handler)
    monkeypatch.setitem(sys.modules, "lightrag.api.auth", fake_module)

    assert app_route_context.resolve_auth_handler(_context()) is fake_auth_handler


def test_build_route_registry_context_hydrates_startup_state_and_auth(monkeypatch):
    fake_auth_handler = object()
    fake_module = SimpleNamespace(auth_handler=fake_auth_handler)
    monkeypatch.setitem(sys.modules, "lightrag.api.auth", fake_module)
    startup_state = SimpleNamespace(
        doc_manager="doc-manager",
        api_key="api-key",
        api_version_display="0256",
        webui_assets_exist=True,
        webui_title="LightRAG",
        webui_description="API",
    )
    args = SimpleNamespace(top_k=5)

    context = app_route_context.build_route_registry_context(
        rag="rag",
        startup_state=startup_state,
        args=args,
        rerank_enabled=True,
    )

    assert context.rag == "rag"
    assert context.doc_manager == "doc-manager"
    assert context.api_key == "api-key"
    assert context.args is args
    assert context.api_version_display == "0256"
    assert context.webui_assets_exist is True
    assert context.webui_title == "LightRAG"
    assert context.webui_description == "API"
    assert context.rerank_enabled is True
    assert context.auth_handler is fake_auth_handler


def test_build_route_registry_context_prefers_explicit_auth_handler():
    override = object()
    startup_state = SimpleNamespace(
        doc_manager="doc-manager",
        api_key="api-key",
        api_version_display="0256",
        webui_assets_exist=False,
        webui_title=None,
        webui_description=None,
    )

    context = app_route_context.build_route_registry_context(
        rag="rag",
        startup_state=startup_state,
        args=SimpleNamespace(top_k=5),
        rerank_enabled=False,
        auth_handler=override,
    )

    assert context.auth_handler is override


def test_route_registry_reexports_route_registry_context_for_compatibility():
    assert route_registry.RouteRegistryContext is app_route_context.RouteRegistryContext
