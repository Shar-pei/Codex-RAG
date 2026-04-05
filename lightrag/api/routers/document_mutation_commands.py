from __future__ import annotations

import traceback

from fastapi import BackgroundTasks, HTTPException

from lightrag import LightRAG
from lightrag.api.routers.document_deletion_pipeline import background_delete_documents
from lightrag.api.routers.document_manager import DocumentManager
from lightrag.api.routers.document_operation_models import (
    ClearCacheRequest,
    ClearCacheResponse,
    DeleteDocByIdResponse,
    DeleteDocRequest,
    DeleteEntityRequest,
    DeleteRelationRequest,
)
from lightrag.base import DeletionResult
from lightrag.utils import logger


async def initiate_document_deletion(
    rag: LightRAG,
    doc_manager: DocumentManager,
    delete_request: DeleteDocRequest,
    background_tasks: BackgroundTasks,
) -> DeleteDocByIdResponse:
    """Check pipeline state and enqueue document deletion work."""
    doc_ids = delete_request.doc_ids

    try:
        from lightrag.kg.shared_storage import (
            get_namespace_data,
            get_namespace_lock,
        )

        pipeline_status = await get_namespace_data(
            "pipeline_status", workspace=rag.workspace
        )
        pipeline_status_lock = get_namespace_lock(
            "pipeline_status", workspace=rag.workspace
        )

        async with pipeline_status_lock:
            if pipeline_status.get("busy", False):
                return DeleteDocByIdResponse(
                    status="busy",
                    message="Cannot delete documents while pipeline is busy",
                    doc_id=", ".join(doc_ids),
                )

        background_tasks.add_task(
            background_delete_documents,
            rag,
            doc_manager,
            doc_ids,
            delete_request.delete_file,
            delete_request.delete_llm_cache,
        )

        return DeleteDocByIdResponse(
            status="deletion_started",
            message=f"Document deletion for {len(doc_ids)} documents has been initiated. Processing will continue in background.",
            doc_id=", ".join(doc_ids),
        )
    except Exception as e:
        error_msg = (
            f"Error initiating document deletion for {delete_request.doc_ids}: {str(e)}"
        )
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


async def clear_cache_response(
    rag: LightRAG, request: ClearCacheRequest
) -> ClearCacheResponse:
    """Clear the LLM response cache."""
    del request
    try:
        await rag.aclear_cache()
        return ClearCacheResponse(
            status="success",
            message="Successfully cleared all cache",
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def delete_entity_response(
    rag: LightRAG, request: DeleteEntityRequest
) -> DeletionResult:
    """Delete one entity and normalize API-facing errors."""
    try:
        result = await rag.adelete_by_entity(entity_name=request.entity_name)
        if result.status == "not_found":
            raise HTTPException(status_code=404, detail=result.message)
        if result.status == "fail":
            raise HTTPException(status_code=500, detail=result.message)
        result.doc_id = ""
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error deleting entity '{request.entity_name}': {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


async def delete_relation_response(
    rag: LightRAG, request: DeleteRelationRequest
) -> DeletionResult:
    """Delete one relation and normalize API-facing errors."""
    try:
        result = await rag.adelete_by_relation(
            source_entity=request.source_entity,
            target_entity=request.target_entity,
        )
        if result.status == "not_found":
            raise HTTPException(status_code=404, detail=result.message)
        if result.status == "fail":
            raise HTTPException(status_code=500, detail=result.message)
        result.doc_id = ""
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            f"Error deleting relation from '{request.source_entity}' to '{request.target_entity}': {str(e)}"
        )
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
