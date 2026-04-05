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


document_indexing_pipeline = _import_router_module(
    "lightrag.api.routers.document_indexing_pipeline"
)


def test_document_routes_reexports_indexing_pipeline_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.pipeline_enqueue_file
        is document_indexing_pipeline.pipeline_enqueue_file
    )
    assert (
        document_routes.pipeline_index_texts
        is document_indexing_pipeline.pipeline_index_texts
    )
    assert (
        document_routes.pipeline_index_files
        is document_indexing_pipeline.pipeline_index_files
    )
    assert (
        document_routes.run_scanning_process
        is document_indexing_pipeline.run_scanning_process
    )


def test_pipeline_index_texts_pads_file_sources_and_processes_queue():
    calls: list[tuple[str, object]] = []

    class DummyRAG:
        async def apipeline_enqueue_documents(self, input, file_paths, track_id):
            calls.append(("enqueue", (input, file_paths, track_id)))

        async def apipeline_process_enqueue_documents(self):
            calls.append(("process", None))

    sources = ["first.txt"]

    asyncio.run(
        document_indexing_pipeline.pipeline_index_texts(
            DummyRAG(),
            ["alpha", "beta"],
            file_sources=sources,
            track_id="track-1",
        )
    )

    assert sources == ["first.txt", "unknown_source"]
    assert calls[0] == (
        "enqueue",
        (["alpha", "beta"], ["first.txt", "unknown_source"], "track-1"),
    )
    assert calls[1] == ("process", None)


def test_pipeline_index_files_sorts_before_enqueueing():
    calls: list[str] = []

    class DummyRAG:
        async def apipeline_process_enqueue_documents(self):
            calls.append("process")

    async def fake_pipeline_enqueue_file(rag, file_path, track_id):
        calls.append(file_path.name)
        return True, track_id

    original_enqueue = document_indexing_pipeline.pipeline_enqueue_file
    original_sort_key = document_indexing_pipeline.get_pinyin_sort_key
    document_indexing_pipeline.pipeline_enqueue_file = fake_pipeline_enqueue_file
    document_indexing_pipeline.get_pinyin_sort_key = lambda value: value
    try:
        asyncio.run(
            document_indexing_pipeline.pipeline_index_files(
                DummyRAG(),
                [Path("b.txt"), Path("a.txt")],
                track_id="track-2",
            )
        )
    finally:
        document_indexing_pipeline.pipeline_enqueue_file = original_enqueue
        document_indexing_pipeline.get_pinyin_sort_key = original_sort_key

    assert calls == ["a.txt", "b.txt", "process"]


def test_run_scanning_process_filters_processed_files():
    captured: list[tuple[list[str], str | None]] = []

    async def fake_pipeline_index_files(rag, file_paths, track_id):
        captured.append(([path.name for path in file_paths], track_id))

    class DummyDocStatus:
        async def get_doc_by_file_path(self, filename):
            if filename == "done.txt":
                return {"status": "processed"}
            return None

    class DummyRAG:
        def __init__(self):
            self.doc_status = DummyDocStatus()

        async def apipeline_process_enqueue_documents(self):
            captured.append((["process-only"], None))

    dummy_manager = SimpleNamespace(
        scan_directory_for_new_files=lambda: [Path("done.txt"), Path("todo.txt")]
    )

    original_pipeline_index_files = document_indexing_pipeline.pipeline_index_files
    document_indexing_pipeline.pipeline_index_files = fake_pipeline_index_files
    try:
        asyncio.run(
            document_indexing_pipeline.run_scanning_process(
                DummyRAG(), dummy_manager, track_id="scan-1"
            )
        )
    finally:
        document_indexing_pipeline.pipeline_index_files = original_pipeline_index_files

    assert captured == [(["todo.txt"], "scan-1")]
