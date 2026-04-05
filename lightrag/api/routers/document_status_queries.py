from __future__ import annotations

import asyncio
import traceback
from typing import Dict, List

from fastapi import HTTPException

from lightrag import LightRAG
from lightrag.base import DocProcessingStatus, DocStatus
from lightrag.api.routers.document_status_models import (
    DocStatusResponse,
    DocsStatusesResponse,
    DocumentsRequest,
    PaginatedDocsResponse,
    PaginationInfo,
    StatusCountsResponse,
    TrackStatusResponse,
    format_datetime,
)
from lightrag.utils import logger


def build_doc_status_response(
    doc_id: str, doc_status: DocProcessingStatus
) -> DocStatusResponse:
    """Normalize a document status record into the API response shape."""
    return DocStatusResponse(
        id=doc_id,
        content_summary=doc_status.content_summary,
        content_length=doc_status.content_length,
        status=doc_status.status,
        created_at=format_datetime(doc_status.created_at),
        updated_at=format_datetime(doc_status.updated_at),
        track_id=doc_status.track_id,
        chunks_count=doc_status.chunks_count,
        error_msg=doc_status.error_msg,
        metadata=doc_status.metadata,
        file_path=doc_status.file_path,
    )


async def get_documents_statuses_response(rag: LightRAG) -> DocsStatusesResponse:
    """Read document statuses grouped by processing state with fair distribution."""
    try:
        statuses = (
            DocStatus.PENDING,
            DocStatus.PROCESSING,
            DocStatus.PREPROCESSED,
            DocStatus.PROCESSED,
            DocStatus.FAILED,
        )

        tasks = [rag.get_docs_by_status(status) for status in statuses]
        results: List[Dict[str, DocProcessingStatus]] = await asyncio.gather(*tasks)

        response = DocsStatusesResponse()
        total_documents = 0
        max_documents = 1000

        status_documents = [
            (statuses[idx], list(result.items())) for idx, result in enumerate(results)
        ]
        status_indices = [0] * len(status_documents)
        current_status_idx = 0

        while total_documents < max_documents:
            has_remaining = False
            for status_idx, (_status, docs_list) in enumerate(status_documents):
                if status_indices[status_idx] < len(docs_list):
                    has_remaining = True
                    break

            if not has_remaining:
                break

            status, docs_list = status_documents[current_status_idx]
            current_index = status_indices[current_status_idx]

            if current_index < len(docs_list):
                doc_id, doc_status = docs_list[current_index]
                if status not in response.statuses:
                    response.statuses[status] = []
                response.statuses[status].append(
                    build_doc_status_response(doc_id, doc_status)
                )
                status_indices[current_status_idx] += 1
                total_documents += 1

            current_status_idx = (current_status_idx + 1) % len(status_documents)

        return response
    except Exception as e:
        logger.error(f"Error GET /documents: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def get_track_status_response(
    rag: LightRAG, track_id: str
) -> TrackStatusResponse:
    """Read document statuses associated with one tracking id."""
    try:
        if not track_id or not track_id.strip():
            raise HTTPException(status_code=400, detail="Track ID cannot be empty")

        track_id = track_id.strip()
        docs_by_track_id = await rag.aget_docs_by_track_id(track_id)

        documents = []
        status_summary = {}

        for doc_id, doc_status in docs_by_track_id.items():
            documents.append(build_doc_status_response(doc_id, doc_status))
            status_key = str(doc_status.status)
            status_summary[status_key] = status_summary.get(status_key, 0) + 1

        return TrackStatusResponse(
            track_id=track_id,
            documents=documents,
            total_count=len(documents),
            status_summary=status_summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting track status for {track_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def get_paginated_documents_response(
    rag: LightRAG, request: DocumentsRequest
) -> PaginatedDocsResponse:
    """Read paginated document statuses and related status counts."""
    try:
        docs_task = rag.doc_status.get_docs_paginated(
            status_filter=request.status_filter,
            page=request.page,
            page_size=request.page_size,
            sort_field=request.sort_field,
            sort_direction=request.sort_direction,
        )
        status_counts_task = rag.doc_status.get_all_status_counts()

        (documents_with_ids, total_count), status_counts = await asyncio.gather(
            docs_task, status_counts_task
        )

        doc_responses = [
            build_doc_status_response(doc_id, doc)
            for doc_id, doc in documents_with_ids
        ]

        total_pages = (total_count + request.page_size - 1) // request.page_size
        pagination = PaginationInfo(
            page=request.page,
            page_size=request.page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=request.page < total_pages,
            has_prev=request.page > 1,
        )

        return PaginatedDocsResponse(
            documents=doc_responses,
            pagination=pagination,
            status_counts=status_counts,
        )
    except Exception as e:
        logger.error(f"Error getting paginated documents: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def get_document_status_counts_response(rag: LightRAG) -> StatusCountsResponse:
    """Read aggregated document status counts."""
    try:
        status_counts = await rag.doc_status.get_all_status_counts()
        return StatusCountsResponse(status_counts=status_counts)
    except Exception as e:
        logger.error(f"Error getting document status counts: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
