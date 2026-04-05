"""
This module contains all query-related routes for the LightRAG API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.utils import logger
from lightrag.api.routers.query_models import (
    QueryDataResponse,
    QueryRequest,
    QueryResponse,
    ReferenceItem as _ReferenceItem,
    StreamChunkResponse as _StreamChunkResponse,
)
from lightrag.api.routers.query_execution import (
    build_query_data_param as _build_query_data_param,
    build_query_text_param as _build_query_text_param,
    execute_query_data_request as _execute_query_data_request,
    execute_query_text_request as _execute_query_text_request,
    normalize_query_data_response as _normalize_query_data_response,
)
from lightrag.api.routers.query_route_descriptions import (
    QUERY_DATA_ROUTE_DESCRIPTION as _QUERY_DATA_ROUTE_DESCRIPTION,
    QUERY_ROUTE_DESCRIPTION as _QUERY_ROUTE_DESCRIPTION,
    QUERY_STREAM_ROUTE_DESCRIPTION as _QUERY_STREAM_ROUTE_DESCRIPTION,
)
from lightrag.api.routers.query_route_docs import (
    QUERY_DATA_ROUTE_RESPONSES as _QUERY_DATA_ROUTE_RESPONSES,
    QUERY_ROUTE_RESPONSES as _QUERY_ROUTE_RESPONSES,
    QUERY_STREAM_ROUTE_RESPONSES as _QUERY_STREAM_ROUTE_RESPONSES,
)
from lightrag.api.routers.query_response_helpers import (
    build_query_response_model as _build_query_response_model,
    build_stream_complete_payload as _build_stream_complete_payload,
    get_query_response_content as _get_query_response_content,
    prepare_query_references as _prepare_query_references,
)
from lightrag.api.routers.query_streaming import (
    build_query_streaming_response as _build_query_streaming_response,
    iter_query_stream_payloads as _iter_query_stream_payloads,
)

router = APIRouter(tags=["query"])

ReferenceItem = _ReferenceItem
StreamChunkResponse = _StreamChunkResponse
QUERY_ROUTE_RESPONSES = _QUERY_ROUTE_RESPONSES
QUERY_STREAM_ROUTE_RESPONSES = _QUERY_STREAM_ROUTE_RESPONSES
QUERY_DATA_ROUTE_RESPONSES = _QUERY_DATA_ROUTE_RESPONSES
QUERY_ROUTE_DESCRIPTION = _QUERY_ROUTE_DESCRIPTION
QUERY_STREAM_ROUTE_DESCRIPTION = _QUERY_STREAM_ROUTE_DESCRIPTION
QUERY_DATA_ROUTE_DESCRIPTION = _QUERY_DATA_ROUTE_DESCRIPTION
build_query_text_param = _build_query_text_param
build_query_data_param = _build_query_data_param
execute_query_text_request = _execute_query_text_request
normalize_query_data_response = _normalize_query_data_response
execute_query_data_request = _execute_query_data_request
prepare_query_references = _prepare_query_references
get_query_response_content = _get_query_response_content
build_query_response_model = _build_query_response_model
build_stream_complete_payload = _build_stream_complete_payload
iter_query_stream_payloads = _iter_query_stream_payloads
build_query_streaming_response = _build_query_streaming_response


def create_query_routes(rag, api_key: Optional[str] = None, top_k: int = 60):
    combined_auth = get_combined_auth_dependency(api_key)

    @router.post(
        "/query",
        response_model=QueryResponse,
        dependencies=[Depends(combined_auth)],
        responses=QUERY_ROUTE_RESPONSES,
        description=QUERY_ROUTE_DESCRIPTION,
    )
    async def query_text(request: QueryRequest):
        try:
            return await execute_query_text_request(rag, request)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/query/stream",
        dependencies=[Depends(combined_auth)],
        responses=QUERY_STREAM_ROUTE_RESPONSES,
        description=QUERY_STREAM_ROUTE_DESCRIPTION,
    )
    async def query_text_stream(request: QueryRequest):
        try:
            # Use the stream parameter from the request, defaulting to True if not specified
            stream_mode = request.stream if request.stream is not None else True
            param = request.to_query_params(stream_mode)

            # Unified approach: always use aquery_llm for all cases
            result = await rag.aquery_llm(request.query, param=param)
            return build_query_streaming_response(
                result,
                include_references=request.include_references,
                include_chunk_content=request.include_chunk_content,
            )
        except Exception as e:
            logger.error(f"Error processing streaming query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/query/data",
        response_model=QueryDataResponse,
        dependencies=[Depends(combined_auth)],
        responses=QUERY_DATA_ROUTE_RESPONSES,
        description=QUERY_DATA_ROUTE_DESCRIPTION,
    )
    async def query_data(request: QueryRequest):
        try:
            return await execute_query_data_request(rag, request)
        except Exception as e:
            logger.error(f"Error processing data query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
