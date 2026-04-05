from __future__ import annotations

import traceback

from fastapi import BackgroundTasks, HTTPException

from lightrag import LightRAG
from lightrag.api.routers.document_operation_models import (
    CancelPipelineResponse,
    ReprocessResponse,
)
from lightrag.api.routers.document_status_models import (
    PipelineStatusResponse,
    format_datetime,
)
from lightrag.utils import generate_track_id, logger


async def get_pipeline_status_response(rag: LightRAG) -> PipelineStatusResponse:
    """Read pipeline status and normalize it for the API response."""
    try:
        from lightrag.kg.shared_storage import (
            get_all_update_flags_status,
            get_namespace_data,
            get_namespace_lock,
        )

        pipeline_status = await get_namespace_data(
            "pipeline_status", workspace=rag.workspace
        )
        pipeline_status_lock = get_namespace_lock(
            "pipeline_status", workspace=rag.workspace
        )
        update_status = await get_all_update_flags_status(workspace=rag.workspace)

        processed_update_status = {}
        for namespace, flags in update_status.items():
            processed_update_status[namespace] = [
                bool(flag.value) if hasattr(flag, "value") else bool(flag)
                for flag in flags
            ]

        async with pipeline_status_lock:
            status_dict = dict(pipeline_status)

        status_dict["update_status"] = processed_update_status

        if "history_messages" in status_dict:
            history_list = list(status_dict["history_messages"])
            total_count = len(history_list)
            if total_count > 1000:
                truncated_count = total_count - 1000
                latest_messages = history_list[-1000:]
                truncation_message = (
                    f"[Truncated history messages: {truncated_count}/{total_count}]"
                )
                status_dict["history_messages"] = [truncation_message] + latest_messages
            else:
                status_dict["history_messages"] = history_list

        if "job_start" in status_dict and status_dict["job_start"]:
            status_dict["job_start"] = format_datetime(status_dict["job_start"])

        return PipelineStatusResponse(**status_dict)
    except Exception as e:
        logger.error(f"Error getting pipeline status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def start_failed_document_reprocessing(
    rag: LightRAG, background_tasks: BackgroundTasks
) -> ReprocessResponse:
    """Queue reprocessing of failed and pending documents."""
    try:
        track_id = generate_track_id("retry")
        background_tasks.add_task(rag.apipeline_process_enqueue_documents)
        logger.info(
            f"Reprocessing of failed documents initiated with track_id: {track_id}"
        )
        return ReprocessResponse(
            status="reprocessing_started",
            message="Reprocessing of failed documents has been initiated in background",
            track_id=track_id,
        )
    except Exception as e:
        logger.error(f"Error initiating reprocessing of failed documents: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def request_pipeline_cancellation(rag: LightRAG) -> CancelPipelineResponse:
    """Set the shared cancellation flag for the active pipeline job."""
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
            if not pipeline_status.get("busy", False):
                return CancelPipelineResponse(
                    status="not_busy",
                    message="Pipeline is not currently running. No cancellation needed.",
                )

            pipeline_status["cancellation_requested"] = True
            cancel_msg = "Pipeline cancellation requested by user"
            logger.info(cancel_msg)
            pipeline_status["latest_message"] = cancel_msg
            pipeline_status["history_messages"].append(cancel_msg)

        return CancelPipelineResponse(
            status="cancellation_requested",
            message="Pipeline cancellation has been requested. Documents will be marked as FAILED.",
        )
    except Exception as e:
        logger.error(f"Error requesting pipeline cancellation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
