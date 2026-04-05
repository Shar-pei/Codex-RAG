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


def test_create_graph_routes_returns_fresh_router_instances():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    first = graph_routes.create_graph_routes(object())
    second = graph_routes.create_graph_routes(object())

    assert first is not second
    assert [route.path for route in first.routes] == [
        "/graph/label/list",
        "/graph/label/popular",
        "/graph/label/search",
        "/graphs",
        "/graph/entity/exists",
        "/graph/entity/edit",
        "/graph/relation/edit",
        "/graph/entity/create",
        "/graph/relation/create",
        "/graph/entities/merge",
    ]
    assert [route.path for route in second.routes] == [
        "/graph/label/list",
        "/graph/label/popular",
        "/graph/label/search",
        "/graphs",
        "/graph/entity/exists",
        "/graph/entity/edit",
        "/graph/relation/edit",
        "/graph/entity/create",
        "/graph/relation/create",
        "/graph/entities/merge",
    ]
    assert [route.path for route in graph_routes.router.routes] == []


def test_create_graph_routes_does_not_accumulate_duplicate_paths_across_calls():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    graph_routes.create_graph_routes(object())
    third = graph_routes.create_graph_routes(object())
    paths = [route.path for route in third.routes]

    assert len(paths) == len(set(paths)) == 10
