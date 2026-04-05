from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_deletion_pipeline = _import_router_module(
    "lightrag.api.routers.document_deletion_pipeline"
)


def test_document_routes_reexports_background_delete_documents():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.background_delete_documents
        is document_deletion_pipeline.background_delete_documents
    )


def test_background_delete_documents_triggers_pending_queue_processing():
    pipeline_status = {
        "busy": False,
        "history_messages": [],
        "latest_message": "",
        "cancellation_requested": False,
        "request_pending": True,
    }

    class DummyLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyRAG:
        def __init__(self):
            self.workspace = "workspace-a"
            self.deleted = []
            self.process_calls = 0

        async def adelete_by_doc_id(self, doc_id, delete_llm_cache=False):
            self.deleted.append((doc_id, delete_llm_cache))
            return SimpleNamespace(
                status="success",
                file_path="unknown_source",
                message="ok",
            )

        async def apipeline_process_enqueue_documents(self):
            self.process_calls += 1

    shared_storage = importlib.import_module("lightrag.kg.shared_storage")
    original_get_namespace_data = shared_storage.get_namespace_data
    original_get_namespace_lock = shared_storage.get_namespace_lock
    dummy_rag = DummyRAG()

    async def fake_get_namespace_data(namespace, workspace=None):
        return pipeline_status

    shared_storage.get_namespace_data = fake_get_namespace_data
    shared_storage.get_namespace_lock = lambda namespace, workspace=None: DummyLock()
    try:
        asyncio.run(
            document_deletion_pipeline.background_delete_documents(
                dummy_rag,
                SimpleNamespace(input_dir=Path(".")),
                ["doc-1"],
                delete_file=False,
                delete_llm_cache=True,
            )
        )
    finally:
        shared_storage.get_namespace_data = original_get_namespace_data
        shared_storage.get_namespace_lock = original_get_namespace_lock

    assert dummy_rag.deleted == [("doc-1", True)]
    assert dummy_rag.process_calls == 1
    assert pipeline_status["busy"] is False
    assert pipeline_status["cancellation_requested"] is False
    assert pipeline_status["pending_requests"] is False
    assert "Deletion completed: 1 successful, 0 failed" in pipeline_status["history_messages"]
