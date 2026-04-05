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


graph_models = _import_router_module("lightrag.api.routers.graph_models")
graph_mutation_commands = _import_router_module(
    "lightrag.api.routers.graph_mutation_commands"
)


def test_graph_routes_reexport_graph_mutation_helpers():
    graph_routes = _import_router_module("lightrag.api.routers.graph_routes")

    assert graph_routes.update_entity_response is (
        graph_mutation_commands.update_entity_response
    )
    assert graph_routes.update_relation_response is (
        graph_mutation_commands.update_relation_response
    )
    assert graph_routes.create_entity_response is (
        graph_mutation_commands.create_entity_response
    )
    assert graph_routes.create_relation_response is (
        graph_mutation_commands.create_relation_response
    )
    assert graph_routes.merge_entities_response is (
        graph_mutation_commands.merge_entities_response
    )


def test_update_entity_response_builds_backward_compatible_summary():
    class RagStub:
        async def aedit_entity(self, **kwargs):
            return {"entity_name": kwargs["entity_name"], "description": "updated"}

    request = graph_models.EntityUpdateRequest(
        entity_name="Elon Msk",
        updated_data={"entity_name": "Elon Musk", "description": "Corrected"},
        allow_rename=True,
        allow_merge=True,
    )

    response = asyncio.run(
        graph_mutation_commands.update_entity_response(RagStub(), request)
    )

    assert response["message"] == "Entity updated successfully"
    assert response["data"] == {
        "entity_name": "Elon Msk",
        "description": "updated",
    }
    assert response["operation_summary"]["operation_status"] == "success"
    assert response["operation_summary"]["final_entity"] == "Elon Musk"
    assert response["operation_summary"]["renamed"] is True


def test_create_relation_response_maps_validation_errors_to_http_400():
    class RagStub:
        async def acreate_relation(self, **kwargs):
            raise ValueError("missing entity")

    request = graph_models.RelationCreateRequest(
        source_entity="Elon Musk",
        target_entity="Tesla",
        relation_data={"description": "CEO"},
    )

    try:
        asyncio.run(graph_mutation_commands.create_relation_response(RagStub(), request))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "missing entity"
    else:
        raise AssertionError("Expected HTTPException")


def test_merge_entities_response_formats_success_message():
    class RagStub:
        async def amerge_entities(self, **kwargs):
            return {"merged_entity": kwargs["target_entity"]}

    request = graph_models.EntityMergeRequest(
        entities_to_change=["Elon Msk", "Ellon Musk"],
        entity_to_change_into="Elon Musk",
    )

    response = asyncio.run(
        graph_mutation_commands.merge_entities_response(RagStub(), request)
    )

    assert response["status"] == "success"
    assert response["message"] == "Successfully merged 2 entities into 'Elon Musk'"
    assert response["data"] == {"merged_entity": "Elon Musk"}
