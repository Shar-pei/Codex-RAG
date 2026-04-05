from __future__ import annotations

import asyncio

from lightrag.api.routers.ollama_request_helpers import estimate_tokens


def normalize_stream_error(exc: Exception) -> str:
    if isinstance(exc, asyncio.CancelledError):
        return "Stream was cancelled by server"
    return f"Provider error: {str(exc)}"


def build_generate_chunk_payload(server_infos, content: str) -> dict:
    return _build_stream_chunk_payload(
        server_infos,
        {"response": content},
    )


def build_chat_chunk_payload(server_infos, content: str) -> dict:
    return _build_stream_chunk_payload(
        server_infos,
        {
            "message": {
                "role": "assistant",
                "content": content,
                "images": None,
            }
        },
    )


def build_generate_done_payload(
    server_infos,
    total_response: str,
    prompt_tokens: int,
    start_time: int,
    first_chunk_time: int | None,
    last_chunk_time: int,
) -> dict:
    return {
        "model": server_infos.LIGHTRAG_MODEL,
        "created_at": server_infos.LIGHTRAG_CREATED_AT,
        "response": "",
        "done": True,
        "done_reason": "stop",
        "context": [],
        **_build_stream_metrics(
            total_response=total_response,
            prompt_tokens=prompt_tokens,
            start_time=start_time,
            first_chunk_time=first_chunk_time,
            last_chunk_time=last_chunk_time,
        ),
    }


def build_chat_done_payload(
    server_infos,
    total_response: str,
    prompt_tokens: int,
    start_time: int,
    first_chunk_time: int | None,
    last_chunk_time: int,
) -> dict:
    return {
        "model": server_infos.LIGHTRAG_MODEL,
        "created_at": server_infos.LIGHTRAG_CREATED_AT,
        "message": {
            "role": "assistant",
            "content": "",
            "images": None,
        },
        "done": True,
        "done_reason": "stop",
        **_build_stream_metrics(
            total_response=total_response,
            prompt_tokens=prompt_tokens,
            start_time=start_time,
            first_chunk_time=first_chunk_time,
            last_chunk_time=last_chunk_time,
        ),
    }


def build_generate_error_payload(server_infos, error_msg: str) -> tuple[dict, dict]:
    error_text = f"\n\nError: {error_msg}"
    return (
        {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": error_text,
            "error": error_text,
            "done": False,
        },
        {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": "",
            "done": True,
        },
    )


def build_chat_error_payload(server_infos, error_msg: str) -> tuple[dict, dict]:
    error_text = f"\n\nError: {error_msg}"
    return (
        {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "message": {
                "role": "assistant",
                "content": error_text,
                "images": None,
            },
            "error": error_text,
            "done": False,
        },
        {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "message": {
                "role": "assistant",
                "content": "",
                "images": None,
            },
            "done": True,
        },
    )


def _build_stream_metrics(
    total_response: str,
    prompt_tokens: int,
    start_time: int,
    first_chunk_time: int | None,
    last_chunk_time: int,
) -> dict:
    if first_chunk_time is None:
        first_chunk_time = start_time

    completion_tokens = estimate_tokens(total_response)
    total_time = last_chunk_time - start_time
    prompt_eval_time = first_chunk_time - start_time
    eval_time = last_chunk_time - first_chunk_time

    return {
        "total_duration": total_time,
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_eval_time,
        "eval_count": completion_tokens,
        "eval_duration": eval_time,
    }


def _build_stream_chunk_payload(server_infos, body: dict) -> dict:
    return {
        "model": server_infos.LIGHTRAG_MODEL,
        "created_at": server_infos.LIGHTRAG_CREATED_AT,
        **body,
        "done": False,
    }
