from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace

from fastapi import BackgroundTasks


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_pipeline_control = _import_router_module(
    "lightrag.api.routers.document_pipeline_control"
)


def test_document_routes_reexport_pipeline_control_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.get_pipeline_status_response
        is document_pipeline_control.get_pipeline_status_response
    )
    assert (
        document_routes.start_failed_document_reprocessing
        is document_pipeline_control.start_failed_document_reprocessing
    )
    assert (
        document_routes.request_pipeline_cancellation
        is document_pipeline_control.request_pipeline_cancellation
    )


def test_get_pipeline_status_response_truncates_history_and_normalizes_flags():
    pipeline_status = {
        "busy": True,
        "job_start": "2026-04-05T12:30:00",
        "history_messages": [f"message-{i}" for i in range(1002)],
    }

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
    original_get_all_update_flags_status = shared_storage.get_all_update_flags_status

    async def fake_get_namespace_data(namespace, workspace=None):
        return pipeline_status

    async def fake_get_all_update_flags_status(workspace=None):
        return {
            "docs": [SimpleNamespace(value=1), 0],
        }

    shared_storage.get_namespace_data = fake_get_namespace_data
    shared_storage.get_namespace_lock = lambda namespace, workspace=None: DummyLock()
    shared_storage.get_all_update_flags_status = fake_get_all_update_flags_status
    try:
        response = asyncio.run(
            document_pipeline_control.get_pipeline_status_response(DummyRAG())
        )
    finally:
        shared_storage.get_namespace_data = original_get_namespace_data
        shared_storage.get_namespace_lock = original_get_namespace_lock
        shared_storage.get_all_update_flags_status = original_get_all_update_flags_status

    assert response.update_status == {"docs": [True, False]}
    assert response.job_start == "2026-04-05T12:30:00"
    assert response.history_messages[0] == "[Truncated history messages: 2/1002]"
    assert response.history_messages[-1] == "message-1001"
    assert len(response.history_messages) == 1001


def test_start_failed_document_reprocessing_enqueues_pipeline_job():
    called = []

    class DummyRAG:
        async def apipeline_process_enqueue_documents(self):
            called.append("process")

    background_tasks = BackgroundTasks()
    original_generate_track_id = document_pipeline_control.generate_track_id
    document_pipeline_control.generate_track_id = lambda prefix: f"{prefix}-123"
    try:
        response = asyncio.run(
            document_pipeline_control.start_failed_document_reprocessing(
                DummyRAG(), background_tasks
            )
        )
    finally:
        document_pipeline_control.generate_track_id = original_generate_track_id

    assert response.status == "reprocessing_started"
    assert response.track_id == "retry-123"
    assert len(background_tasks.tasks) == 1
    asyncio.run(background_tasks.tasks[0].func())
    assert called == ["process"]


def test_request_pipeline_cancellation_sets_shared_flag():
    pipeline_status = {
        "busy": True,
        "cancellation_requested": False,
        "latest_message": "",
        "history_messages": [],
    }

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
    try:
        response = asyncio.run(
            document_pipeline_control.request_pipeline_cancellation(DummyRAG())
        )
    finally:
        shared_storage.get_namespace_data = original_get_namespace_data
        shared_storage.get_namespace_lock = original_get_namespace_lock

    assert response.status == "cancellation_requested"
    assert pipeline_status["cancellation_requested"] is True
    assert pipeline_status["latest_message"] == "Pipeline cancellation requested by user"
    assert pipeline_status["history_messages"] == ["Pipeline cancellation requested by user"]
