from __future__ import annotations

import asyncio
import json
import re
import time

from fastapi import HTTPException

from lightrag import QueryParam
from lightrag.api.routers.ollama_models import SearchMode
from lightrag.api.routers.ollama_request_helpers import (
    estimate_tokens,
    parse_query_mode,
)
from lightrag.api.routers.ollama_streaming_responses import (
    build_ollama_streaming_response,
)
from lightrag.utils import logger


async def execute_chat_request(rag, server_infos, request, top_k):
    messages = request.messages
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    if messages[-1].role != "user":
        raise HTTPException(
            status_code=400, detail="Last message must be from user role"
        )

    query = messages[-1].content
    conversation_history = [
        {"role": message.role, "content": message.content}
        for message in messages[:-1]
    ]

    cleaned_query, mode, only_need_context, user_prompt = parse_query_mode(query)
    start_time = time.time_ns()
    prompt_tokens = estimate_tokens(cleaned_query)
    query_param = _build_query_param(
        request=request,
        conversation_history=conversation_history,
        mode=mode,
        only_need_context=only_need_context,
        user_prompt=user_prompt,
        top_k=top_k,
    )

    if request.stream:
        response = await _resolve_streaming_chat_response(
            rag=rag,
            request=request,
            cleaned_query=cleaned_query,
            conversation_history=conversation_history,
            mode=mode,
            query_param=query_param,
        )
        return build_ollama_streaming_response(
            iter_chat_stream_payloads(
                response=response,
                server_infos=server_infos,
                prompt_tokens=prompt_tokens,
                start_time=start_time,
            )
        )

    first_chunk_time = time.time_ns()
    response_text = await _resolve_non_stream_chat_response(
        rag=rag,
        request=request,
        cleaned_query=cleaned_query,
        conversation_history=conversation_history,
        mode=mode,
        query_param=query_param,
    )
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
        "message": {
            "role": "assistant",
            "content": str(response_text),
            "images": None,
        },
        "done_reason": "stop",
        "done": True,
        "total_duration": total_time,
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_eval_time,
        "eval_count": completion_tokens,
        "eval_duration": eval_time,
    }


async def iter_chat_stream_payloads(response, server_infos, prompt_tokens, start_time):
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
            "message": {
                "role": "assistant",
                "content": response,
                "images": None,
            },
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
            "message": {
                "role": "assistant",
                "content": "",
                "images": None,
            },
            "done_reason": "stop",
            "done": True,
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
                    "message": {
                        "role": "assistant",
                        "content": chunk,
                        "images": None,
                    },
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
            "message": {
                "role": "assistant",
                "content": f"\n\nError: {error_msg}",
                "images": None,
            },
            "error": f"\n\nError: {error_msg}",
            "done": False,
        }
        yield f"{json.dumps(error_data, ensure_ascii=False)}\n"

        final_data = {
            "model": server_infos.LIGHTRAG_MODEL,
            "created_at": server_infos.LIGHTRAG_CREATED_AT,
            "message": {
                "role": "assistant",
                "content": "",
                "images": None,
            },
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
        "message": {
            "role": "assistant",
            "content": "",
            "images": None,
        },
        "done_reason": "stop",
        "done": True,
        "total_duration": total_time,
        "load_duration": 0,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_eval_time,
        "eval_count": completion_tokens,
        "eval_duration": eval_time,
    }
    yield f"{json.dumps(data, ensure_ascii=False)}\n"


def _build_query_param(
    request,
    conversation_history,
    mode,
    only_need_context,
    user_prompt,
    top_k,
):
    param_dict = {
        "mode": mode.value,
        "stream": request.stream,
        "only_need_context": only_need_context,
        "conversation_history": conversation_history,
        "top_k": top_k,
    }
    if user_prompt is not None:
        param_dict["user_prompt"] = user_prompt
    return QueryParam(**param_dict)


async def _resolve_streaming_chat_response(
    rag,
    request,
    cleaned_query,
    conversation_history,
    mode,
    query_param,
):
    if mode == SearchMode.bypass:
        _apply_system_prompt(rag, request.system)
        return await rag.llm_model_func(
            cleaned_query,
            stream=True,
            history_messages=conversation_history,
            **rag.llm_model_kwargs,
        )

    return await rag.aquery(cleaned_query, param=query_param)


async def _resolve_non_stream_chat_response(
    rag,
    request,
    cleaned_query,
    conversation_history,
    mode,
    query_param,
):
    if _should_use_direct_llm(cleaned_query, mode):
        _apply_system_prompt(rag, request.system)
        return await rag.llm_model_func(
            cleaned_query,
            stream=False,
            history_messages=conversation_history,
            **rag.llm_model_kwargs,
        )

    return await rag.aquery(cleaned_query, param=query_param)


def _should_use_direct_llm(cleaned_query, mode):
    return mode == SearchMode.bypass or bool(
        re.search(r"\n<chat_history>\nUSER:", cleaned_query, re.MULTILINE)
    )


def _apply_system_prompt(rag, system_prompt):
    if system_prompt:
        rag.llm_model_kwargs["system_prompt"] = system_prompt
