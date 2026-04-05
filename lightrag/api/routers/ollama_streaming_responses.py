from __future__ import annotations

from fastapi.responses import StreamingResponse


OLLAMA_STREAMING_MEDIA_TYPE = "application/x-ndjson"
OLLAMA_STREAMING_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": OLLAMA_STREAMING_MEDIA_TYPE,
    "X-Accel-Buffering": "no",
}


def build_ollama_streaming_response(body_iterator) -> StreamingResponse:
    return StreamingResponse(
        body_iterator,
        media_type=OLLAMA_STREAMING_MEDIA_TYPE,
        headers=OLLAMA_STREAMING_HEADERS,
    )
