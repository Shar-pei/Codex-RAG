from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_manager_module = _import_router_module(
    "lightrag.api.routers.document_manager"
)


def test_document_routes_reexports_document_manager_seam():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert document_routes.DocumentManager is document_manager_module.DocumentManager
    assert document_routes.sanitize_filename is document_manager_module.sanitize_filename
    assert (
        document_routes.validate_file_path_security
        is document_manager_module.validate_file_path_security
    )
    assert (
        document_routes.get_unique_filename_in_enqueued
        is document_manager_module.get_unique_filename_in_enqueued
    )


def test_document_manager_uses_workspace_subdirectory_and_scans_new_files():
    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        temp_path = Path(temp_dir)
        manager = document_manager_module.DocumentManager(
            input_dir=str(temp_path),
            workspace="workspace-a",
            supported_extensions=(".txt", ".md"),
        )
        text_file = manager.input_dir / "note.txt"
        markdown_file = manager.input_dir / "guide.md"
        ignored_file = manager.input_dir / "image.png"
        text_file.write_text("hello", encoding="utf-8")
        markdown_file.write_text("world", encoding="utf-8")
        ignored_file.write_text("binary?", encoding="utf-8")

        assert manager.input_dir == temp_path / "workspace-a"
        assert manager.is_supported_file("README.MD")

        scanned = manager.scan_directory_for_new_files()

        assert scanned == [markdown_file, text_file] or scanned == [
            text_file,
            markdown_file,
        ]

        manager.mark_as_indexed(text_file)
        rescanned = manager.scan_directory_for_new_files()
        assert text_file not in rescanned
        assert markdown_file in rescanned


def test_sanitize_filename_rejects_empty_or_invalid_names():
    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        temp_path = Path(temp_dir)

        with pytest.raises(HTTPException, match="Filename cannot be empty"):
            document_manager_module.sanitize_filename("   ", temp_path)

        with pytest.raises(HTTPException, match="Invalid filename after sanitization"):
            document_manager_module.sanitize_filename("..", temp_path)


def test_validate_file_path_security_blocks_traversal_and_normalizes_safe_paths():
    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        temp_path = Path(temp_dir)
        safe = document_manager_module.validate_file_path_security(
            " nested\\\\doc.txt ",
            temp_path,
        )
        blocked = document_manager_module.validate_file_path_security(
            "../secret.txt", temp_path
        )

        assert safe == (temp_path / "nested" / "doc.txt").resolve()
        assert blocked is None


def test_get_unique_filename_in_enqueued_adds_numeric_suffix():
    with tempfile.TemporaryDirectory(dir=".") as temp_dir:
        target_dir = Path(temp_dir)
        (target_dir / "report.txt").write_text("existing", encoding="utf-8")

        unique_name = document_manager_module.get_unique_filename_in_enqueued(
            target_dir, "report.txt"
        )

        assert unique_name == "report_001.txt"
