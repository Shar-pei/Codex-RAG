from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from lightrag.kg.shared_storage import (
    cleanup_keyed_lock,
    get_default_workspace,
    get_namespace_data,
)
from lightrag.utils import logger


def create_health_router(
    context: Any,
    combined_auth: Any,
    auth_handler: Any,
    version_payload: dict[str, Any],
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health",
        dependencies=[Depends(combined_auth)],
        summary="Get system health and configuration status",
        description="Returns comprehensive system status including WebUI availability, configuration, and operational metrics",
        response_description="System health status with configuration details",
        responses={
            200: {
                "description": "Successful response with system status",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "healthy",
                            "webui_available": True,
                            "working_directory": "/path/to/working/dir",
                            "input_directory": "/path/to/input/dir",
                            "configuration": {
                                "llm_binding": "openai",
                                "llm_model": "gpt-4",
                                "embedding_binding": "openai",
                                "embedding_model": "text-embedding-ada-002",
                                "workspace": "default",
                            },
                            "auth_mode": "enabled",
                            "pipeline_busy": False,
                            "core_version": "0.0.1",
                            "api_version": "0.0.1",
                        }
                    }
                },
            }
        },
    )
    async def get_status(request: Request):
        try:
            workspace = _get_workspace_from_request(request)
            default_workspace = get_default_workspace()
            if workspace is None:
                workspace = default_workspace

            pipeline_status = await get_namespace_data(
                "pipeline_status",
                workspace=workspace,
            )
            auth_mode = "enabled" if auth_handler.accounts else "disabled"
            keyed_lock_info = cleanup_keyed_lock()

            return {
                "status": "healthy",
                "webui_available": context.webui_assets_exist,
                "working_directory": str(context.args.working_dir),
                "input_directory": str(context.args.input_dir),
                "configuration": _build_health_configuration(
                    context=context,
                    default_workspace=default_workspace,
                ),
                "auth_mode": auth_mode,
                "pipeline_busy": pipeline_status.get("busy", False),
                "keyed_locks": keyed_lock_info,
                **version_payload,
            }
        except Exception as exc:
            logger.error(f"Error getting health status: {str(exc)}")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router


def _get_workspace_from_request(request: Request) -> str | None:
    workspace = request.headers.get("LIGHTRAG-WORKSPACE", "").strip()
    return workspace or None


def _build_health_configuration(context: Any, default_workspace: str) -> dict[str, Any]:
    return {
        "llm_binding": context.args.llm_binding,
        "llm_binding_host": context.args.llm_binding_host,
        "llm_model": context.args.llm_model,
        "embedding_binding": context.args.embedding_binding,
        "embedding_binding_host": context.args.embedding_binding_host,
        "embedding_model": context.args.embedding_model,
        "summary_max_tokens": context.args.summary_max_tokens,
        "summary_context_size": context.args.summary_context_size,
        "kv_storage": context.args.kv_storage,
        "doc_status_storage": context.args.doc_status_storage,
        "graph_storage": context.args.graph_storage,
        "vector_storage": context.args.vector_storage,
        "enable_llm_cache_for_extract": context.args.enable_llm_cache_for_extract,
        "enable_llm_cache": context.args.enable_llm_cache,
        "workspace": default_workspace,
        "max_graph_nodes": context.args.max_graph_nodes,
        "enable_rerank": context.rerank_enabled,
        "rerank_binding": context.args.rerank_binding,
        "rerank_model": context.args.rerank_model if context.rerank_enabled else None,
        "rerank_binding_host": (
            context.args.rerank_binding_host if context.rerank_enabled else None
        ),
        "summary_language": context.args.summary_language,
        "force_llm_summary_on_merge": context.args.force_llm_summary_on_merge,
        "max_parallel_insert": context.args.max_parallel_insert,
        "cosine_threshold": context.args.cosine_threshold,
        "min_rerank_score": context.args.min_rerank_score,
        "related_chunk_number": context.args.related_chunk_number,
        "max_async": context.args.max_async,
        "embedding_func_max_async": context.args.embedding_func_max_async,
        "embedding_batch_num": context.args.embedding_batch_num,
    }
