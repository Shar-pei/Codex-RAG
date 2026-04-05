from __future__ import annotations

import importlib
import sys

import pytest


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_operation_models = _import_router_module(
    "lightrag.api.routers.document_operation_models"
)


def test_document_routes_reexports_extracted_operation_models():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert document_routes.InsertTextRequest is document_operation_models.InsertTextRequest
    assert document_routes.DeleteDocRequest is document_operation_models.DeleteDocRequest
    assert (
        document_routes.DeleteDocByIdResponse
        is document_operation_models.DeleteDocByIdResponse
    )
    assert (
        document_routes.ClearCacheResponse
        is document_operation_models.ClearCacheResponse
    )


def test_insert_text_request_strips_text_and_source():
    request = document_operation_models.InsertTextRequest(
        text="  hello world  ",
        file_source="  sample.txt  ",
    )

    assert request.text == "hello world"
    assert request.file_source == "sample.txt"


def test_delete_doc_request_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="Document IDs must be unique"):
        document_operation_models.DeleteDocRequest(doc_ids=["doc-1", " doc-1 "])


def test_delete_relation_request_strips_entity_names():
    request = document_operation_models.DeleteRelationRequest(
        source_entity="  Alice  ",
        target_entity="  Bob  ",
    )

    assert request.source_entity == "Alice"
    assert request.target_entity == "Bob"
