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


graph_route_descriptions = _import_router_module(
    "lightrag.api.routers.graph_route_descriptions"
)


def test_graph_routes_reexport_graph_route_descriptions():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    assert graph_routes.KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION is (
        graph_route_descriptions.KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION
    )
    assert graph_routes.ENTITY_EDIT_ROUTE_DESCRIPTION is (
        graph_route_descriptions.ENTITY_EDIT_ROUTE_DESCRIPTION
    )
    assert graph_routes.ENTITY_CREATE_ROUTE_DESCRIPTION is (
        graph_route_descriptions.ENTITY_CREATE_ROUTE_DESCRIPTION
    )
    assert graph_routes.RELATION_CREATE_ROUTE_DESCRIPTION is (
        graph_route_descriptions.RELATION_CREATE_ROUTE_DESCRIPTION
    )
    assert graph_routes.ENTITY_MERGE_ROUTE_DESCRIPTION is (
        graph_route_descriptions.ENTITY_MERGE_ROUTE_DESCRIPTION
    )


def test_graph_route_descriptions_keep_key_sections():
    assert "connected subgraph" in (
        graph_route_descriptions.KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION
    )
    assert "partial_success" in graph_route_descriptions.ENTITY_EDIT_ROUTE_DESCRIPTION
    assert "vector embeddings" in (
        graph_route_descriptions.ENTITY_CREATE_ROUTE_DESCRIPTION
    )
    assert "undirected relationship" in (
        graph_route_descriptions.RELATION_CREATE_ROUTE_DESCRIPTION
    )
    assert "duplicate or misspelled entities" in (
        graph_route_descriptions.ENTITY_MERGE_ROUTE_DESCRIPTION
    )


def test_create_graph_routes_uses_extracted_descriptions():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")
    router = graph_routes.create_graph_routes(object())
    route_by_path = {route.path: route for route in router.routes}

    assert route_by_path["/graphs"].description == (
        graph_routes.KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION
    )
    assert route_by_path["/graph/entity/edit"].description == (
        graph_routes.ENTITY_EDIT_ROUTE_DESCRIPTION
    )
    assert route_by_path["/graph/entity/create"].description == (
        graph_routes.ENTITY_CREATE_ROUTE_DESCRIPTION
    )
    assert route_by_path["/graph/relation/create"].description == (
        graph_routes.RELATION_CREATE_ROUTE_DESCRIPTION
    )
    assert route_by_path["/graph/entities/merge"].description == (
        graph_routes.ENTITY_MERGE_ROUTE_DESCRIPTION
    )
