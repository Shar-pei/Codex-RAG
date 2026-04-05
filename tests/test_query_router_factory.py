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


def test_create_query_routes_returns_fresh_router_instances():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    first = query_routes.create_query_routes(object())
    second = query_routes.create_query_routes(object())

    assert first is not second
    assert [route.path for route in first.routes] == [
        "/query",
        "/query/stream",
        "/query/data",
    ]
    assert [route.path for route in second.routes] == [
        "/query",
        "/query/stream",
        "/query/data",
    ]
    assert [route.path for route in query_routes.router.routes] == []


def test_create_query_routes_does_not_accumulate_duplicate_paths_across_calls():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    query_routes.create_query_routes(object())
    third = query_routes.create_query_routes(object())
    paths = [route.path for route in third.routes]

    assert len(paths) == len(set(paths)) == 3
