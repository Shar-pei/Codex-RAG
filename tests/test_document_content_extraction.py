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


document_content_extraction = _import_router_module(
    "lightrag.api.routers.document_content_extraction"
)


def test_document_routes_reexports_content_extraction_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes._is_docling_available
        is document_content_extraction._is_docling_available
    )
    assert (
        document_routes._extract_xlsx is document_content_extraction._extract_xlsx
    )
    assert (
        document_routes._extract_docx is document_content_extraction._extract_docx
    )


def test_escape_tabular_cell_preserves_visible_delimiters():
    escaped = document_content_extraction._escape_tabular_cell(
        "alpha\\beta\tgamma\r\ndelta\nepsilon"
    )

    assert escaped == "alpha\\\\beta\\tgamma\\ndelta\\nepsilon"


def test_escape_tabular_cell_handles_none():
    assert document_content_extraction._escape_tabular_cell(None) == ""


def test_sanitize_sheet_title_replaces_tabs_and_newlines():
    sanitized = document_content_extraction._sanitize_sheet_title("A\tB\r\nC\nD")

    assert sanitized == "A B  C D"
