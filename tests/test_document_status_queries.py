from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime

from lightrag.base import DocProcessingStatus, DocStatus


def _import_router_module(module_name: str):
    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        return importlib.import_module(module_name)
    finally:
        sys.argv = original_argv


document_status_queries = _import_router_module(
    "lightrag.api.routers.document_status_queries"
)


def _make_doc(doc_id: str, status: DocStatus) -> tuple[str, DocProcessingStatus]:
    return (
        doc_id,
        DocProcessingStatus(
            content_summary=f"summary-{doc_id}",
            content_length=len(doc_id),
            file_path=f"{doc_id}.txt",
            status=status,
            created_at=datetime(2026, 4, 5, 12, 0, 0),
            updated_at=datetime(2026, 4, 5, 13, 0, 0),
            track_id="track-1",
            chunks_count=1,
            error_msg=None,
            metadata={"doc_id": doc_id},
        ),
    )


def test_document_routes_reexport_status_query_helpers():
    document_routes = _import_router_module("lightrag.api.routers.document_routes")

    assert (
        document_routes.build_doc_status_response
        is document_status_queries.build_doc_status_response
    )
    assert (
        document_routes.get_documents_statuses_response
        is document_status_queries.get_documents_statuses_response
    )
    assert (
        document_routes.get_track_status_response
        is document_status_queries.get_track_status_response
    )
    assert (
        document_routes.get_paginated_documents_response
        is document_status_queries.get_paginated_documents_response
    )
    assert (
        document_routes.get_document_status_counts_response
        is document_status_queries.get_document_status_counts_response
    )


def test_get_documents_statuses_response_round_robins_when_capped():
    pending_docs = dict(
        _make_doc(f"pending-{idx}", DocStatus.PENDING) for idx in range(700)
    )
    processed_docs = dict(
        _make_doc(f"processed-{idx}", DocStatus.PROCESSED) for idx in range(700)
    )

    class DummyRAG:
        async def get_docs_by_status(self, status):
            if status == DocStatus.PENDING:
                return pending_docs
            if status == DocStatus.PROCESSED:
                return processed_docs
            return {}

    response = asyncio.run(
        document_status_queries.get_documents_statuses_response(DummyRAG())
    )

    assert len(response.statuses[DocStatus.PENDING]) == 500
    assert len(response.statuses[DocStatus.PROCESSED]) == 500


def test_get_track_status_response_strips_track_id_and_summarizes_statuses():
    docs = dict(
        [
            _make_doc("doc-a", DocStatus.PENDING),
            _make_doc("doc-b", DocStatus.PROCESSED),
            _make_doc("doc-c", DocStatus.PROCESSED),
        ]
    )

    class DummyRAG:
        async def aget_docs_by_track_id(self, track_id):
            assert track_id == "track-1"
            return docs

    response = asyncio.run(
        document_status_queries.get_track_status_response(DummyRAG(), "  track-1  ")
    )

    assert response.track_id == "track-1"
    assert response.total_count == 3
    assert response.status_summary == {"DocStatus.PENDING": 1, "DocStatus.PROCESSED": 2}


def test_get_paginated_documents_response_calculates_pagination_and_maps_docs():
    class DummyDocStatus:
        async def get_docs_paginated(
            self,
            status_filter=None,
            page=1,
            page_size=10,
            sort_field=None,
            sort_direction=None,
        ):
            return ([
                _make_doc("doc-a", DocStatus.PROCESSED),
                _make_doc("doc-b", DocStatus.FAILED),
            ], 25)

        async def get_all_status_counts(self):
            return {"processed": 4, "failed": 1}

    class DummyRAG:
        doc_status = DummyDocStatus()

    request = _import_router_module(
        "lightrag.api.routers.document_status_models"
    ).DocumentsRequest(page=2, page_size=10)

    response = asyncio.run(
        document_status_queries.get_paginated_documents_response(DummyRAG(), request)
    )

    assert [doc.id for doc in response.documents] == ["doc-a", "doc-b"]
    assert response.pagination.total_pages == 3
    assert response.pagination.has_next is True
    assert response.pagination.has_prev is True
    assert response.status_counts == {"processed": 4, "failed": 1}
