from __future__ import annotations

import shutil
import traceback

from fastapi import BackgroundTasks, HTTPException, UploadFile

from lightrag import LightRAG
from lightrag.api.routers.document_indexing_pipeline import (
    pipeline_index_file,
    pipeline_index_texts,
    run_scanning_process,
)
from lightrag.api.routers.document_manager import DocumentManager, sanitize_filename
from lightrag.api.routers.document_operation_models import (
    InsertResponse,
    InsertTextRequest,
    InsertTextsRequest,
    ScanResponse,
)
from lightrag.utils import generate_track_id, logger


async def start_scan_for_new_documents(
    rag: LightRAG,
    doc_manager: DocumentManager,
    background_tasks: BackgroundTasks,
) -> ScanResponse:
    """Start a background scan of the document input directory."""
    track_id = generate_track_id("scan")
    background_tasks.add_task(run_scanning_process, rag, doc_manager, track_id)
    return ScanResponse(
        status="scanning_started",
        message="Scanning process has been initiated in the background",
        track_id=track_id,
    )


async def upload_file_to_input_dir(
    rag: LightRAG,
    doc_manager: DocumentManager,
    background_tasks: BackgroundTasks,
    file: UploadFile,
) -> InsertResponse:
    """Save an uploaded file and enqueue it for indexing."""
    try:
        safe_filename = sanitize_filename(file.filename, doc_manager.input_dir)

        if not doc_manager.is_supported_file(safe_filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {doc_manager.supported_extensions}",
            )

        existing_doc_data = await rag.doc_status.get_doc_by_file_path(safe_filename)
        if existing_doc_data:
            status = existing_doc_data.get("status", "unknown")
            return InsertResponse(
                status="duplicated",
                message=f"File '{safe_filename}' already exists in document storage (Status: {status}).",
                track_id="",
            )

        file_path = doc_manager.input_dir / safe_filename
        if file_path.exists():
            return InsertResponse(
                status="duplicated",
                message=f"File '{safe_filename}' already exists in the input directory.",
                track_id="",
            )

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        track_id = generate_track_id("upload")
        background_tasks.add_task(pipeline_index_file, rag, file_path, track_id)

        return InsertResponse(
            status="success",
            message=f"File '{safe_filename}' uploaded successfully. Processing will continue in background.",
            track_id=track_id,
        )
    except Exception as e:
        logger.error(f"Error /documents/upload: {file.filename}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def insert_single_text(
    rag: LightRAG,
    request: InsertTextRequest,
    background_tasks: BackgroundTasks,
) -> InsertResponse:
    """Validate and enqueue one text document."""
    try:
        if (
            request.file_source
            and request.file_source.strip()
            and request.file_source != "unknown_source"
        ):
            existing_doc_data = await rag.doc_status.get_doc_by_file_path(
                request.file_source
            )
            if existing_doc_data:
                status = existing_doc_data.get("status", "unknown")
                return InsertResponse(
                    status="duplicated",
                    message=f"File source '{request.file_source}' already exists in document storage (Status: {status}).",
                    track_id="",
                )

        track_id = generate_track_id("insert")
        background_tasks.add_task(
            pipeline_index_texts,
            rag,
            [request.text],
            file_sources=[request.file_source],
            track_id=track_id,
        )

        return InsertResponse(
            status="success",
            message="Text successfully received. Processing will continue in background.",
            track_id=track_id,
        )
    except Exception as e:
        logger.error(f"Error /documents/text: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def insert_multiple_texts(
    rag: LightRAG,
    request: InsertTextsRequest,
    background_tasks: BackgroundTasks,
) -> InsertResponse:
    """Validate and enqueue multiple text documents."""
    try:
        if request.file_sources:
            for file_source in request.file_sources:
                if (
                    file_source
                    and file_source.strip()
                    and file_source != "unknown_source"
                ):
                    existing_doc_data = await rag.doc_status.get_doc_by_file_path(
                        file_source
                    )
                    if existing_doc_data:
                        status = existing_doc_data.get("status", "unknown")
                        return InsertResponse(
                            status="duplicated",
                            message=f"File source '{file_source}' already exists in document storage (Status: {status}).",
                            track_id="",
                        )

        track_id = generate_track_id("insert")
        background_tasks.add_task(
            pipeline_index_texts,
            rag,
            request.texts,
            file_sources=request.file_sources,
            track_id=track_id,
        )

        return InsertResponse(
            status="success",
            message="Texts successfully received. Processing will continue in background.",
            track_id=track_id,
        )
    except Exception as e:
        logger.error(f"Error /documents/texts: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
