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


def _route_signatures(router):
    signatures = []
    for route in router.routes:
        methods = tuple(sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"}))
        signatures.append((route.path, methods))
    return signatures


def test_create_document_routes_returns_fresh_router_instances():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    first = document_routes.create_document_routes(object(), object())
    second = document_routes.create_document_routes(object(), object())

    expected = [
        ("/documents/scan", ("POST",)),
        ("/documents/upload", ("POST",)),
        ("/documents/text", ("POST",)),
        ("/documents/texts", ("POST",)),
        ("/documents", ("DELETE",)),
        ("/documents/pipeline_status", ("GET",)),
        ("/documents", ("GET",)),
        ("/documents/delete_document", ("DELETE",)),
        ("/documents/clear_cache", ("POST",)),
        ("/documents/delete_entity", ("DELETE",)),
        ("/documents/delete_relation", ("DELETE",)),
        ("/documents/track_status/{track_id}", ("GET",)),
        ("/documents/paginated", ("POST",)),
        ("/documents/status_counts", ("GET",)),
        ("/documents/reprocess_failed", ("POST",)),
        ("/documents/cancel_pipeline", ("POST",)),
    ]

    assert first is not second
    assert _route_signatures(first) == expected
    assert _route_signatures(second) == expected
    assert _route_signatures(document_routes.router) == []


def test_create_document_routes_does_not_accumulate_duplicate_routes_across_calls():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    document_routes.create_document_routes(object(), object())
    third = document_routes.create_document_routes(object(), object())
    signatures = _route_signatures(third)

    assert len(signatures) == len(set(signatures)) == 16
