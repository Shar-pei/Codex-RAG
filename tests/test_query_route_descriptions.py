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


query_route_descriptions = _import_router_module(
    "lightrag.api.routers.query_route_descriptions"
)


def test_query_routes_reexport_query_route_descriptions():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")

    assert query_routes.QUERY_ROUTE_DESCRIPTION is (
        query_route_descriptions.QUERY_ROUTE_DESCRIPTION
    )
    assert query_routes.QUERY_STREAM_ROUTE_DESCRIPTION is (
        query_route_descriptions.QUERY_STREAM_ROUTE_DESCRIPTION
    )
    assert query_routes.QUERY_DATA_ROUTE_DESCRIPTION is (
        query_route_descriptions.QUERY_DATA_ROUTE_DESCRIPTION
    )


def test_query_route_descriptions_keep_key_sections():
    assert "Retrieval-Augmented Generation" in (
        query_route_descriptions.QUERY_ROUTE_DESCRIPTION
    )
    assert "NDJSON" in query_route_descriptions.QUERY_STREAM_ROUTE_DESCRIPTION
    assert "structured RAG analysis" in (
        query_route_descriptions.QUERY_DATA_ROUTE_DESCRIPTION
    )


def test_create_query_routes_uses_extracted_descriptions():
    query_routes = _import_router_module("lightrag.api.routers.query_routes")
    router = query_routes.create_query_routes(object())
    route_by_path = {route.path: route for route in router.routes}

    assert route_by_path["/query"].description == query_routes.QUERY_ROUTE_DESCRIPTION
    assert route_by_path["/query/stream"].description == (
        query_routes.QUERY_STREAM_ROUTE_DESCRIPTION
    )
    assert route_by_path["/query/data"].description == (
        query_routes.QUERY_DATA_ROUTE_DESCRIPTION
    )
