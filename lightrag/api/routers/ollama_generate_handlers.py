from __future__ import annotations

import asyncio
import json
import time

from fastapi.responses import StreamingResponse

from lightrag.api.routers.ollama_request_helpers import estimate_tokens
from lightrag.utils import logger


async def execute_generate_request(rag, server_infos, request):
    query = request.prompt
    start_time = time.time_ns()
    prompt_tokens = estimate_tokens(query)

    if request.system:
        rag.llm_model_kwargs["system_prompt"] = request.system

    if request.stream:
        response = await rag.llm_model_func(query, stream=True, **rag.llm_model_kwargs)
        return StreamingResponse(
            iter_generate_stream_payloads(
                response=response,
                server_infos=server_infos,
                prompt_tokens=prompt_tokens,
                start_time=start_time,
            ),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/x-ndjson",
                "X-Accel-Buffering": "no",
            },
        )

    first_chunk_time = time.time_ns()
    response_text = await rag.llm_model_func(query, stream=False, **rag.llm_model_kwargs)
    last_chunk_time = time.time_ns()

    if not response_text:
        response_text = "No response generated"

    completion_tokens = estimate_tokens(str(response_text))
    total_time = last_chunk_time - start_time
    prompt_eval_time = first_chunk_time - start_time
    eval_time = last_chunk_time - first_chunk_time

    return {
        "model": server_infos.LIGHTRAG_MODEL,
        "created_at": server_infos.LIGHTRAG_CREATED_AT,
        "response": str(response_text),
        "done": True,
        "done_reason": "stop",
        "context": [],
        "total_duration": total_time,
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_eval_time,
        "eval_count": completion_tokens,
        "eval_duration": eval_time,
    }


async def iter_generate_stream_payloads(response, server_infos, prompt_tokens, start_time):
    first_chunk_time = None
    last_chunk_time = time.time_ns()
    total_response = ""

    if isinstance(response, str):
        first_chunk_time = start_time
        last_chunk_time = time.time_ns()
        total_response = response

        data = {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": response,
            "done": False,
        }
        yield f"{json.dumps(data, ensure_ascii=False)}\n"

        completion_tokens = estimate_tokens(total_response)
        total_time = last_chunk_time - start_time
        prompt_eval_time = first_chunk_time - start_time
        eval_time = last_chunk_time - first_chunk_time

        data = {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": "",
            "done": True,
            "done_reason": "stop",
            "context": [],
            "total_duration": total_time,
            "load_duration": 0,
            "prompt_eval_count": prompt_tokens,
            "prompt_eval_duration": prompt_eval_time,
            "eval_count": completion_tokens,
            "eval_duration": eval_time,
        }
        yield f"{json.dumps(data, ensure_ascii=False)}\n"
        return

    try:
        async for chunk in response:
            if chunk:
                if first_chunk_time is None:
                    first_chunk_time = time.time_ns()

                last_chunk_time = time.time_ns()
                total_response += chunk
                data = {
                    "model": server_infos.LIGHTRAG_MODEL,
                    "created_at": server_infos.LIGHTRAG_CREATED_AT,
                    "response": chunk,
                    "done": False,
                }
                yield f"{json.dumps(data, ensure_ascii=False)}\n"
    except (asyncio.CancelledError, Exception) as exc:
        error_msg = str(exc)
        if isinstance(exc, asyncio.CancelledError):
            error_msg = "Stream was cancelled by server"
        else:
            error_msg = f"Provider error: {error_msg}"

        logger.error(f"Stream error: {error_msg}")

        error_data = {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": f"\n\nError: {error_msg}",
            "error": f"\n\nError: {error_msg}",
            "done": False,
        }
        yield f"{json.dumps(error_data, ensure_ascii=False)}\n"

        final_data = {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "response": "",
            "done": True,
        }
        yield f"{json.dumps(final_data, ensure_ascii=False)}\n"
        return

    if first_chunk_time is None:
        first_chunk_time = start_time
    completion_tokens = estimate_tokens(total_response)
    total_time = last_chunk_time - start_time
    prompt_eval_time = first_chunk_time - start_time
    eval_time = last_chunk_time - first_chunk_time

    data = {
        "model": server_infos.LIGHTRAG_MODEL,
        "created_at": server_infos.LIGHTRAG_CREATED_AT,
        "response": "",
        "done": True,
        "done_reason": "stop",
        "context": [],
        "total_duration": total_time,
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_eval_time,
        "eval_count": completion_tokens,
        "eval_duration": eval_time,
    }
    yield f"{json.dumps(data, ensure_ascii=False)}\n"
