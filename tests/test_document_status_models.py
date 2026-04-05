from __future__ import annotations

import importlib
import sys
from datetime import datetime


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_status_models = _import_router_module(
    "lightrag.api.routers.document_status_models"
)


def test_document_routes_reexports_extracted_status_models():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert document_routes.DocStatusResponse is document_status_models.DocStatusResponse
    assert (
        document_routes.DocsStatusesResponse
        is document_status_models.DocsStatusesResponse
    )
    assert (
        document_routes.PipelineStatusResponse
        is document_status_models.PipelineStatusResponse
    )


def test_pipeline_status_model_formats_naive_datetimes_as_utc():
    response = document_status_models.PipelineStatusResponse(
        job_start=datetime(2026, 4, 5, 12, 30, 0)
    )

    assert response.job_start == "2026-04-05T12:30:00+00:00"


def test_documents_request_keeps_pagination_defaults():
    request = document_status_models.DocumentsRequest()

    assert request.page == 1
    assert request.page_size == 50
    assert request.sort_field == "updated_at"
    assert request.sort_direction == "desc"
