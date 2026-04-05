from __future__ import annotations

import asyncio
import importlib
import sys
import tempfile
from pathlib import Path


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_clear_pipeline = _import_router_module(
    "lightrag.api.routers.document_clear_pipeline"
)


def test_document_routes_reexports_clear_documents_pipeline():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.clear_documents_pipeline
        is document_clear_pipeline.clear_documents_pipeline
    )


def test_clear_documents_pipeline_drops_active_storages_and_only_deletes_top_level_files():
    pipeline_status = {
        "busy": False,
        "history_messages": [],
        "latest_message": "",
    }

    class DummyLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyStorage:
        def __init__(self, name: str):
            self.namespace = name
            self.workspace = "workspace-a"
            self.drop_calls = 0

        async def drop(self):
            self.drop_calls += 1

    class DummyRAG:
        def __init__(self, active_storage):
            self.workspace = "workspace-a"
            self.text_chunks = None
            self.full_docs = active_storage
            self.full_entities = None
            self.full_relations = None
            self.entity_chunks = None
            self.relation_chunks = None
            self.entities_vdb = None
            self.relationships_vdb = None
            self.chunks_vdb = None
            self.chunk_entity_relation_graph = None
            self.doc_status = None

    shared_storage = importlib.import_module("lightrag.kg.shared_storage")
    original_get_namespace_data = shared_storage.get_namespace_data
    original_get_namespace_lock = shared_storage.get_namespace_lock

    async def fake_get_namespace_data(namespace, workspace=None):
        return pipeline_status

    shared_storage.get_namespace_data = fake_get_namespace_data
    shared_storage.get_namespace_lock = lambda namespace, workspace=None: DummyLock()
    storage = DummyStorage("full_docs")

    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        input_dir = Path(temp_dir)
        top_level_file = input_dir / "note.txt"
        nested_dir = input_dir / "nested"
        nested_dir.mkdir()
        nested_file = nested_dir / "keep.txt"
        top_level_file.write_text("delete me", encoding="utf-8")
        nested_file.write_text("keep me", encoding="utf-8")

        try:
            response = asyncio.run(
                document_clear_pipeline.clear_documents_pipeline(
                    DummyRAG(storage),
                    type("DummyManager", (), {"input_dir": input_dir})(),
                )
            )
        finally:
            shared_storage.get_namespace_data = original_get_namespace_data
            shared_storage.get_namespace_lock = original_get_namespace_lock

        assert response.status == "success"
        assert response.message == "All documents cleared successfully. Deleted 1 files."
        assert storage.drop_calls == 1
        assert not top_level_file.exists()
        assert nested_file.exists()
        assert pipeline_status["busy"] is False
        assert pipeline_status["latest_message"] == "Document clearing process completed"
        assert "Successfully dropped all 1 storage components" in pipeline_status["history_messages"]
        assert "Successfully deleted 1 files" in pipeline_status["history_messages"]
