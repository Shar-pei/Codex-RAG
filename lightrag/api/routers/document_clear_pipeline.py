from __future__ import annotations

import asyncio
from datetime import datetime
import traceback

from fastapi import HTTPException

from lightrag import LightRAG
from lightrag.api.routers.document_manager import DocumentManager
from lightrag.api.routers.document_operation_models import ClearDocumentsResponse
from lightrag.utils import logger


async def clear_documents_pipeline(
    rag: LightRAG, doc_manager: DocumentManager
) -> ClearDocumentsResponse:
    """Clear all indexed document data and remove input files."""
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
            return ClearDocumentsResponse(
                status="busy",
                message="Cannot clear documents while pipeline is busy",
            )

        pipeline_status.update(
            {
                "busy": True,
                "job_name": "Clearing Documents",
                "job_start": datetime.now().isoformat(),
                "docs": 0,
                "batchs": 0,
                "cur_batch": 0,
                "request_pending": False,
                "latest_message": "Starting document clearing process",
            }
        )
        del pipeline_status["history_messages"][:]
        pipeline_status["history_messages"].append("Starting document clearing process")

    try:
        storages = [
            rag.text_chunks,
            rag.full_docs,
            rag.full_entities,
            rag.full_relations,
            rag.entity_chunks,
            rag.relation_chunks,
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.chunks_vdb,
            rag.chunk_entity_relation_graph,
            rag.doc_status,
        ]
        active_storages = [storage for storage in storages if storage is not None]

        if "history_messages" in pipeline_status:
            pipeline_status["history_messages"].append(
                "Starting to drop storage components"
            )

        drop_results = await asyncio.gather(
            *(storage.drop() for storage in active_storages),
            return_exceptions=True,
        )

        errors = []
        storage_success_count = 0
        storage_error_count = 0

        for storage, result in zip(active_storages, drop_results):
            storage_name = storage.__class__.__name__
            if isinstance(result, Exception):
                error_msg = f"Error dropping {storage_name}: {str(result)}"
                errors.append(error_msg)
                logger.error(error_msg)
                storage_error_count += 1
            else:
                logger.info(
                    f"Successfully dropped {storage_name}: {storage.workspace}/{storage.namespace}"
                )
                storage_success_count += 1

        if "history_messages" in pipeline_status:
            if storage_error_count > 0:
                pipeline_status["history_messages"].append(
                    f"Dropped {storage_success_count} storage components with {storage_error_count} errors"
                )
            else:
                pipeline_status["history_messages"].append(
                    f"Successfully dropped all {storage_success_count} storage components"
                )

        if storage_success_count == 0 and storage_error_count > 0:
            error_message = (
                "All storage drop operations failed. Aborting document clearing process."
            )
            logger.error(error_message)
            if "history_messages" in pipeline_status:
                pipeline_status["history_messages"].append(error_message)
            return ClearDocumentsResponse(status="fail", message=error_message)

        if "history_messages" in pipeline_status:
            pipeline_status["history_messages"].append(
                "Starting to delete files in input directory"
            )

        deleted_files_count = 0
        file_errors_count = 0

        for file_path in doc_manager.input_dir.glob("*"):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_files_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")
                    file_errors_count += 1

        if "history_messages" in pipeline_status:
            if file_errors_count > 0:
                pipeline_status["history_messages"].append(
                    f"Deleted {deleted_files_count} files with {file_errors_count} errors"
                )
                errors.append(f"Failed to delete {file_errors_count} files")
            else:
                pipeline_status["history_messages"].append(
                    f"Successfully deleted {deleted_files_count} files"
                )

        if errors:
            final_message = (
                f"Cleared documents with some errors. Deleted {deleted_files_count} files."
            )
            status = "partial_success"
        else:
            final_message = (
                f"All documents cleared successfully. Deleted {deleted_files_count} files."
            )
            status = "success"

        if "history_messages" in pipeline_status:
            pipeline_status["history_messages"].append(final_message)

        return ClearDocumentsResponse(status=status, message=final_message)
    except Exception as e:
        error_msg = f"Error clearing documents: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if "history_messages" in pipeline_status:
            pipeline_status["history_messages"].append(error_msg)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        async with pipeline_status_lock:
            pipeline_status["busy"] = False
            completion_msg = "Document clearing process completed"
            pipeline_status["latest_message"] = completion_msg
            if "history_messages" in pipeline_status:
                pipeline_status["history_messages"].append(completion_msg)
