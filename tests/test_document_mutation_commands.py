from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_mutation_commands = _import_router_module(
    "lightrag.api.routers.document_mutation_commands"
)
document_operation_models = _import_router_module(
    "lightrag.api.routers.document_operation_models"
)


def test_document_routes_reexport_mutation_command_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.initiate_document_deletion
        is document_mutation_commands.initiate_document_deletion
    )
    assert (
        document_routes.clear_cache_response
        is document_mutation_commands.clear_cache_response
    )
    assert (
        document_routes.delete_entity_response
        is document_mutation_commands.delete_entity_response
    )
    assert (
        document_routes.delete_relation_response
        is document_mutation_commands.delete_relation_response
    )


def test_initiate_document_deletion_returns_busy_without_scheduling_task():
    pipeline_status = {"busy": True}

    class DummyLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyRAG:
        workspace = "workspace-a"

    shared_storage = importlib.import_module("lightrag.kg.shared_storage")
    original_get_namespace_data = shared_storage.get_namespace_data
    original_get_namespace_lock = shared_storage.get_namespace_lock

    async def fake_get_namespace_data(namespace, workspace=None):
        return pipeline_status

    shared_storage.get_namespace_data = fake_get_namespace_data
    shared_storage.get_namespace_lock = lambda namespace, workspace=None: DummyLock()
    background_tasks = BackgroundTasks()
    try:
        response = asyncio.run(
            document_mutation_commands.initiate_document_deletion(
                DummyRAG(),
                SimpleNamespace(),
                document_operation_models.DeleteDocRequest(doc_ids=["doc-1"]),
                background_tasks,
            )
        )
    finally:
        shared_storage.get_namespace_data = original_get_namespace_data
        shared_storage.get_namespace_lock = original_get_namespace_lock

    assert response.status == "busy"
    assert response.doc_id == "doc-1"
    assert background_tasks.tasks == []


def test_clear_cache_response_calls_rag_cache_clear():
    calls = []

    class DummyRAG:
        async def aclear_cache(self):
            calls.append("cleared")

    response = asyncio.run(
        document_mutation_commands.clear_cache_response(
            DummyRAG(),
            document_operation_models.ClearCacheRequest(),
        )
    )

    assert response.status == "success"
    assert response.message == "Successfully cleared all cache"
    assert calls == ["cleared"]


def test_delete_entity_response_sets_doc_id_on_success():
    class DummyRAG:
        async def adelete_by_entity(self, entity_name):
            assert entity_name == "Alice"
            return SimpleNamespace(status="success", message="ok", doc_id="doc-1")

    response = asyncio.run(
        document_mutation_commands.delete_entity_response(
            DummyRAG(),
            document_operation_models.DeleteEntityRequest(entity_name="Alice"),
        )
    )

    assert response.status == "success"
    assert response.doc_id == ""


def test_delete_relation_response_maps_not_found_to_http_404():
    class DummyRAG:
        async def adelete_by_relation(self, source_entity, target_entity):
            return SimpleNamespace(status="not_found", message="missing", doc_id="")

    with pytest.raises(HTTPException, match="missing") as exc_info:
        asyncio.run(
            document_mutation_commands.delete_relation_response(
                DummyRAG(),
                document_operation_models.DeleteRelationRequest(
                    source_entity="Alice",
                    target_entity="Bob",
                ),
            )
        )

    assert exc_info.value.status_code == 404
