from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi.responses import StreamingResponse

from lightrag.api.routers.query_response_helpers import (
    build_stream_complete_payload,
    prepare_query_references,
)
from lightrag.utils import logger


async def iter_query_stream_payloads(
    result: dict[str, Any],
    include_references: bool,
    include_chunk_content: bool,
) -> AsyncIterator[str]:
    """Yield NDJSON payload lines for the /query/stream endpoint."""
    data = result.get("data", {})
    references = prepare_query_references(
        data,
        include_references=include_references,
        include_chunk_content=include_chunk_content,
    )
    llm_response = result.get("llm_response", {})

    if llm_response.get("is_streaming"):
        if references is not None:
            yield f"{json.dumps({'references': references})}\n"

        response_stream = llm_response.get("response_iterator")
        if response_stream:
            try:
                async for chunk in response_stream:
                    if chunk:
                        yield f"{json.dumps({'response': chunk})}\n"
            except Exception as exc:
                logger.error(f"Streaming error: {str(exc)}")
                yield f"{json.dumps({'error': str(exc)})}\n"
        return

    complete_response = build_stream_complete_payload(llm_response, references)
    yield f"{json.dumps(complete_response)}\n"


def build_query_streaming_response(
    result: dict[str, Any],
    include_references: bool,
    include_chunk_content: bool,
) -> StreamingResponse:
    """Build the FastAPI streaming response for /query/stream."""
    return StreamingResponse(
        iter_query_stream_payloads(
            result,
            include_references=include_references,
            include_chunk_content=include_chunk_content,
        ),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/x-ndjson",
            "X-Accel-Buffering": "no",
        },
    )
