from __future__ import annotations

import asyncio
import importlib
import sys

from fastapi import HTTPException


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


graph_query_helpers = _import_router_module("lightrag.api.routers.graph_query_helpers")


def test_graph_routes_reexport_graph_query_helpers():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    assert graph_routes.get_graph_labels_response is (
        graph_query_helpers.get_graph_labels_response
    )
    assert graph_routes.get_popular_labels_response is (
        graph_query_helpers.get_popular_labels_response
    )
    assert graph_routes.search_labels_response is (
        graph_query_helpers.search_labels_response
    )
    assert graph_routes.get_knowledge_graph_response is (
        graph_query_helpers.get_knowledge_graph_response
    )
    assert graph_routes.check_entity_exists_response is (
        graph_query_helpers.check_entity_exists_response
    )


def test_get_popular_labels_response_uses_graph_backend_limit():
    class GraphStub:
        async def get_popular_labels(self, limit):
            return [f"top-{limit}"]

    class RagStub:
        chunk_entity_relation_graph = GraphStub()

    response = asyncio.run(
        graph_query_helpers.get_popular_labels_response(RagStub(), 7)
    )

    assert response == ["top-7"]


def test_get_knowledge_graph_response_passes_query_arguments():
    class RagStub:
        async def get_knowledge_graph(self, **kwargs):
            return kwargs

    response = asyncio.run(
        graph_query_helpers.get_knowledge_graph_response(
            RagStub(), "Tesla", 3, 1000
        )
    )

    assert response == {
        "node_label": "Tesla",
        "max_depth": 3,
        "max_nodes": 1000,
    }


def test_search_labels_response_maps_failures_to_http_500():
    class GraphStub:
        async def search_labels(self, q, limit):
            raise RuntimeError(f"boom-{q}-{limit}")

    class RagStub:
        chunk_entity_relation_graph = GraphStub()

    try:
        asyncio.run(graph_query_helpers.search_labels_response(RagStub(), "tes", 5))
    except HTTPException as exc:
        assert exc.status_code == 500
        assert exc.detail == "Error searching labels: boom-tes-5"
    else:
        raise AssertionError("Expected HTTPException")


def test_check_entity_exists_response_wraps_boolean_result():
    class GraphStub:
        async def has_node(self, name):
            return name == "Tesla"

    class RagStub:
        chunk_entity_relation_graph = GraphStub()

    response = asyncio.run(
        graph_query_helpers.check_entity_exists_response(RagStub(), "Tesla")
    )

    assert response == {"exists": True}
