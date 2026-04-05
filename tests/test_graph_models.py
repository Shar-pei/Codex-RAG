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


graph_models = _import_router_module("lightrag.api.routers.graph_models")


def test_graph_routes_reexport_extracted_graph_models():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    assert graph_routes.EntityUpdateRequest is graph_models.EntityUpdateRequest
    assert graph_routes.RelationUpdateRequest is graph_models.RelationUpdateRequest
    assert graph_routes.EntityMergeRequest is graph_models.EntityMergeRequest
    assert graph_routes.EntityCreateRequest is graph_models.EntityCreateRequest
    assert graph_routes.RelationCreateRequest is graph_models.RelationCreateRequest


def test_entity_update_request_keeps_rename_and_merge_defaults():
    request = graph_models.EntityUpdateRequest(
        entity_name="Tesla",
        updated_data={"description": "Updated"},
    )

    assert request.allow_rename is False
    assert request.allow_merge is False


def test_entity_merge_request_requires_non_empty_source_entities():
    request = graph_models.EntityMergeRequest(
        entities_to_change=["Elon Msk"],
        entity_to_change_into="Elon Musk",
    )

    assert request.entities_to_change == ["Elon Msk"]
    assert request.entity_to_change_into == "Elon Musk"


def test_relation_create_request_keeps_nested_relation_payload():
    request = graph_models.RelationCreateRequest(
        source_entity="Elon Musk",
        target_entity="Tesla",
        relation_data={"description": "CEO", "weight": 1.0},
    )

    assert request.source_entity == "Elon Musk"
    assert request.target_entity == "Tesla"
    assert request.relation_data["weight"] == 1.0
