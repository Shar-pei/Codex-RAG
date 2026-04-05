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


def test_route_registry_reexports_route_registry_context_for_compatibility():
    assert route_registry.RouteRegistryContext is app_route_context.RouteRegistryContext
