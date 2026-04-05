from __future__ import annotations

from typing import Any

from lightrag.api.routers.query_models import QueryDataResponse, QueryRequest
from lightrag.api.routers.query_response_helpers import build_query_response_model


def build_query_text_param(request: QueryRequest):
    """Build query params for the non-streaming /query endpoint."""
    param = request.to_query_params(False)
    param.stream = False
    return param


def build_query_data_param(request: QueryRequest):
    """Build query params for the /query/data endpoint."""
    return request.to_query_params(False)


async def execute_query_text_request(rag: Any, request: QueryRequest):
    """Execute a non-streaming query request and build its response model."""
    result = await rag.aquery_llm(request.query, param=build_query_text_param(request))
    return build_query_response_model(
        result,
        include_references=request.include_references,
        include_chunk_content=request.include_chunk_content,
    )


def normalize_query_data_response(response: Any) -> QueryDataResponse:
    """Normalize /query/data results into the public response model."""
    if isinstance(response, dict):
        return QueryDataResponse(**response)

    return QueryDataResponse(
        status="failure",
        message="Invalid response type",
        data={},
        metadata={},
    )


async def execute_query_data_request(rag: Any, request: QueryRequest) -> QueryDataResponse:
    """Execute a /query/data request and normalize the returned payload."""
    response = await rag.aquery_data(request.query, param=build_query_data_param(request))
    return normalize_query_data_response(response)
