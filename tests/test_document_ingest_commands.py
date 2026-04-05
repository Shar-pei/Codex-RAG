from __future__ import annotations

import asyncio
import importlib
import io
import sys
import tempfile
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_ingest_commands = _import_router_module(
    "lightrag.api.routers.document_ingest_commands"
)
document_operation_models = _import_router_module(
    "lightrag.api.routers.document_operation_models"
)


def test_document_routes_reexport_ingest_command_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.start_scan_for_new_documents
        is document_ingest_commands.start_scan_for_new_documents
    )
    assert (
        document_routes.upload_file_to_input_dir
        is document_ingest_commands.upload_file_to_input_dir
    )
    assert (
        document_routes.insert_single_text
        is document_ingest_commands.insert_single_text
    )
    assert (
        document_routes.insert_multiple_texts
        is document_ingest_commands.insert_multiple_texts
    )


def test_start_scan_for_new_documents_schedules_background_scan():
    background_tasks = BackgroundTasks()
    original_generate_track_id = document_ingest_commands.generate_track_id
    document_ingest_commands.generate_track_id = lambda prefix: f"{prefix}-123"
    try:
        response = asyncio.run(
            document_ingest_commands.start_scan_for_new_documents(
                object(),
                object(),
                background_tasks,
            )
        )
    finally:
        document_ingest_commands.generate_track_id = original_generate_track_id

    assert response.status == "scanning_started"
    assert response.track_id == "scan-123"
    assert len(background_tasks.tasks) == 1


def test_upload_file_to_input_dir_returns_duplicate_when_doc_exists():
    class DummyDocStatus:
        async def get_doc_by_file_path(self, file_path):
            assert file_path == "report.txt"
            return {"status": "processed"}

    class DummyRAG:
        doc_status = DummyDocStatus()

    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        input_dir = Path(temp_dir)
        doc_manager = type(
            "DummyManager",
            (),
            {
                "input_dir": input_dir,
                "supported_extensions": (".txt",),
                "is_supported_file": staticmethod(lambda filename: True),
            },
        )()
        file = UploadFile(filename="report.txt", file=io.BytesIO(b"hello"))

        response = asyncio.run(
            document_ingest_commands.upload_file_to_input_dir(
                DummyRAG(),
                doc_manager,
                BackgroundTasks(),
                file,
            )
        )

    assert response.status == "duplicated"
    assert "already exists in document storage" in response.message


def test_insert_single_text_enqueues_background_processing():
    background_tasks = BackgroundTasks()
    original_generate_track_id = document_ingest_commands.generate_track_id
    document_ingest_commands.generate_track_id = lambda prefix: f"{prefix}-123"

    class DummyDocStatus:
        async def get_doc_by_file_path(self, file_path):
            return None

    class DummyRAG:
        doc_status = DummyDocStatus()

    try:
        response = asyncio.run(
            document_ingest_commands.insert_single_text(
                DummyRAG(),
                document_operation_models.InsertTextRequest(
                    text="hello",
                    file_source="note.txt",
                ),
                background_tasks,
            )
        )
    finally:
        document_ingest_commands.generate_track_id = original_generate_track_id

    assert response.status == "success"
    assert response.track_id == "insert-123"
    assert len(background_tasks.tasks) == 1


def test_insert_multiple_texts_returns_duplicate_for_existing_source():
    class DummyDocStatus:
        async def get_doc_by_file_path(self, file_path):
            if file_path == "dup.txt":
                return {"status": "processed"}
            return None

    class DummyRAG:
        doc_status = DummyDocStatus()

    response = asyncio.run(
        document_ingest_commands.insert_multiple_texts(
            DummyRAG(),
            document_operation_models.InsertTextsRequest(
                texts=["one", "two"],
                file_sources=["dup.txt", "new.txt"],
            ),
            BackgroundTasks(),
        )
    )

    assert response.status == "duplicated"
    assert "dup.txt" in response.message
