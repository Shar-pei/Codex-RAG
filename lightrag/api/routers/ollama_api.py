import asyncio
import time
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from lightrag import LightRAG, QueryParam
from lightrag.api.routers.ollama_models import (
    OllamaChatRequest as _OllamaChatRequest,
    OllamaChatResponse as _OllamaChatResponse,
    OllamaGenerateRequest as _OllamaGenerateRequest,
    OllamaGenerateResponse as _OllamaGenerateResponse,
    OllamaMessage as _OllamaMessage,
    OllamaModel as _OllamaModel,
    OllamaModelDetails as _OllamaModelDetails,
    OllamaPsResponse as _OllamaPsResponse,
    OllamaRunningModel as _OllamaRunningModel,
    OllamaRunningModelDetails as _OllamaRunningModelDetails,
    OllamaTagResponse as _OllamaTagResponse,
    OllamaVersionResponse as _OllamaVersionResponse,
    SearchMode as _SearchMode,
)
from lightrag.api.routers.ollama_request_helpers import (
    estimate_tokens as _estimate_tokens,
    parse_query_mode as _parse_query_mode,
    parse_request_body as _parse_request_body,
)
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.utils import logger


SearchMode = _SearchMode
OllamaMessage = _OllamaMessage
OllamaChatRequest = _OllamaChatRequest
OllamaChatResponse = _OllamaChatResponse
OllamaGenerateRequest = _OllamaGenerateRequest
OllamaGenerateResponse = _OllamaGenerateResponse
OllamaVersionResponse = _OllamaVersionResponse
OllamaModelDetails = _OllamaModelDetails
OllamaModel = _OllamaModel
OllamaTagResponse = _OllamaTagResponse
OllamaRunningModelDetails = _OllamaRunningModelDetails
OllamaRunningModel = _OllamaRunningModel
OllamaPsResponse = _OllamaPsResponse
parse_request_body = _parse_request_body
estimate_tokens = _estimate_tokens
parse_query_mode = _parse_query_mode


class OllamaAPI:
    def __init__(self, rag: LightRAG, top_k: int = 60, api_key: Optional[str] = None):
        self.rag = rag
        self.ollama_server_infos = rag.ollama_server_infos
        self.top_k = top_k
        self.api_key = api_key
        self.router = APIRouter(tags=["ollama"])
        self.setup_routes()

    def setup_routes(self):
        # Create combined auth dependency for Ollama API routes
        combined_auth = get_combined_auth_dependency(self.api_key)

        @self.router.get("/version", dependencies=[Depends(combined_auth)])
        async def get_version():
            """Get Ollama version information"""
            return OllamaVersionResponse(version="0.9.3")

        @self.router.get("/tags", dependencies=[Depends(combined_auth)])
        async def get_tags():
            """Return available models acting as an Ollama server"""
            return OllamaTagResponse(
                models=[
                    {
                        "name": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "modified_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                        "size": self.ollama_server_infos.LIGHTRAG_SIZE,
                        "digest": self.ollama_server_infos.LIGHTRAG_DIGEST,
                        "details": {
                            "parent_model": "",
                            "format": "gguf",
                            "family": self.ollama_server_infos.LIGHTRAG_NAME,
                            "families": [self.ollama_server_infos.LIGHTRAG_NAME],
                            "parameter_size": "13B",
                            "quantization_level": "Q4_0",
                        },
                    }
                ]
            )

        @self.router.get("/ps", dependencies=[Depends(combined_auth)])
        async def get_running_models():
            """List Running Models - returns currently running models"""
            return OllamaPsResponse(
                models=[
                    {
                        "name": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "size": self.ollama_server_infos.LIGHTRAG_SIZE,
                        "digest": self.ollama_server_infos.LIGHTRAG_DIGEST,
                        "details": {
                            "parent_model": "",
                            "format": "gguf",
                            "family": "llama",
                            "families": ["llama"],
                            "parameter_size": "7.2B",
                            "quantization_level": "Q4_0",
                        },
                        "expires_at": "2050-12-31T14:38:31.83753-07:00",
                        "size_vram": self.ollama_server_infos.LIGHTRAG_SIZE,
                    }
                ]
            )

        @self.router.post(
            "/generate", dependencies=[Depends(combined_auth)], include_in_schema=True
        )
        async def generate(raw_request: Request):
            """Handle generate completion requests acting as an Ollama model
            For compatibility purpose, the request is not processed by LightRAG,
            and will be handled by underlying LLM model.
            Supports both application/json and application/octet-stream Content-Types.
            """
            try:
                # Parse the request body manually
                request = await parse_request_body(raw_request, OllamaGenerateRequest)

                query = request.prompt
                start_time = time.time_ns()
                prompt_tokens = estimate_tokens(query)

                if request.system:
                    self.rag.llm_model_kwargs["system_prompt"] = request.system

                if request.stream:
                    response = await self.rag.llm_model_func(
                        query, stream=True, **self.rag.llm_model_kwargs
                    )

                    async def stream_generator():
                        first_chunk_time = None
                        last_chunk_time = time.time_ns()
                        total_response = ""

                        # Ensure response is an async generator
                        if isinstance(response, str):
                            # If it's a string, send in two parts
                            first_chunk_time = start_time
                            last_chunk_time = time.time_ns()
                            total_response = response

                            data = {
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                                "response": response,
                                "done": False,
                            }
                            yield f"{json.dumps(data, ensure_ascii=False)}\n"

                            completion_tokens = estimate_tokens(total_response)
                            total_time = last_chunk_time - start_time
                            prompt_eval_time = first_chunk_time - start_time
                            eval_time = last_chunk_time - first_chunk_time

                            data = {
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
                        else:
                            try:
                                async for chunk in response:
                                    if chunk:
                                        if first_chunk_time is None:
                                            first_chunk_time = time.time_ns()

                                        last_chunk_time = time.time_ns()

                                        total_response += chunk
                                        data = {
                                            "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                            "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                                            "response": chunk,
                                            "done": False,
                                        }
                                        yield f"{json.dumps(data, ensure_ascii=False)}\n"
                            except (asyncio.CancelledError, Exception) as e:
                                error_msg = str(e)
                                if isinstance(e, asyncio.CancelledError):
                                    error_msg = "Stream was cancelled by server"
                                else:
                                    error_msg = f"Provider error: {error_msg}"

                                logger.error(f"Stream error: {error_msg}")

                                # Send error message to client
                                error_data = {
                                    "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                    "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                                    "response": f"\n\nError: {error_msg}",
                                    "error": f"\n\nError: {error_msg}",
                                    "done": False,
                                }
                                yield f"{json.dumps(error_data, ensure_ascii=False)}\n"

                                # Send final message to close the stream
                                final_data = {
                                    "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                    "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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

                    return StreamingResponse(
                        stream_generator(),
                        media_type="application/x-ndjson",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Content-Type": "application/x-ndjson",
                            "X-Accel-Buffering": "no",  # Ensure proper handling of streaming responses in Nginx proxy
                        },
                    )
                else:
                    first_chunk_time = time.time_ns()
                    response_text = await self.rag.llm_model_func(
                        query, stream=False, **self.rag.llm_model_kwargs
                    )
                    last_chunk_time = time.time_ns()

                    if not response_text:
                        response_text = "No response generated"

                    completion_tokens = estimate_tokens(str(response_text))
                    total_time = last_chunk_time - start_time
                    prompt_eval_time = first_chunk_time - start_time
                    eval_time = last_chunk_time - first_chunk_time

                    return {
                        "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
            except Exception as e:
                logger.error(f"Ollama generate error: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post(
            "/chat", dependencies=[Depends(combined_auth)], include_in_schema=True
        )
        async def chat(raw_request: Request):
            """Process chat completion requests by acting as an Ollama model.
            Routes user queries through LightRAG by selecting query mode based on query prefix.
            Detects and forwards OpenWebUI session-related requests (for meta data generation task) directly to LLM.
            Supports both application/json and application/octet-stream Content-Types.
            """
            try:
                # Parse the request body manually
                request = await parse_request_body(raw_request, OllamaChatRequest)

                # Get all messages
                messages = request.messages
                if not messages:
                    raise HTTPException(status_code=400, detail="No messages provided")

                # Validate that the last message is from a user
                if messages[-1].role != "user":
                    raise HTTPException(
                        status_code=400, detail="Last message must be from user role"
                    )

                # Get the last message as query and previous messages as history
                query = messages[-1].content
                # Convert OllamaMessage objects to dictionaries
                conversation_history = [
                    {"role": msg.role, "content": msg.content} for msg in messages[:-1]
                ]

                # Check for query prefix
                cleaned_query, mode, only_need_context, user_prompt = parse_query_mode(
                    query
                )

                start_time = time.time_ns()
                prompt_tokens = estimate_tokens(cleaned_query)

                param_dict = {
                    "mode": mode.value,
                    "stream": request.stream,
                    "only_need_context": only_need_context,
                    "conversation_history": conversation_history,
                    "top_k": self.top_k,
                }

                # Add user_prompt to param_dict
                if user_prompt is not None:
                    param_dict["user_prompt"] = user_prompt

                query_param = QueryParam(**param_dict)

                if request.stream:
                    # Determine if the request is prefix with "/bypass"
                    if mode == SearchMode.bypass:
                        if request.system:
                            self.rag.llm_model_kwargs["system_prompt"] = request.system
                        response = await self.rag.llm_model_func(
                            cleaned_query,
                            stream=True,
                            history_messages=conversation_history,
                            **self.rag.llm_model_kwargs,
                        )
                    else:
                        response = await self.rag.aquery(
                            cleaned_query, param=query_param
                        )

                    async def stream_generator():
                        first_chunk_time = None
                        last_chunk_time = time.time_ns()
                        total_response = ""

                        # Ensure response is an async generator
                        if isinstance(response, str):
                            # If it's a string, send in two parts
                            first_chunk_time = start_time
                            last_chunk_time = time.time_ns()
                            total_response = response

                            data = {
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
                        else:
                            try:
                                async for chunk in response:
                                    if chunk:
                                        if first_chunk_time is None:
                                            first_chunk_time = time.time_ns()

                                        last_chunk_time = time.time_ns()

                                        total_response += chunk
                                        data = {
                                            "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                            "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                                            "message": {
                                                "role": "assistant",
                                                "content": chunk,
                                                "images": None,
                                            },
                                            "done": False,
                                        }
                                        yield f"{json.dumps(data, ensure_ascii=False)}\n"
                            except (asyncio.CancelledError, Exception) as e:
                                error_msg = str(e)
                                if isinstance(e, asyncio.CancelledError):
                                    error_msg = "Stream was cancelled by server"
                                else:
                                    error_msg = f"Provider error: {error_msg}"

                                logger.error(f"Stream error: {error_msg}")

                                # Send error message to client
                                error_data = {
                                    "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                    "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
                                    "message": {
                                        "role": "assistant",
                                        "content": f"\n\nError: {error_msg}",
                                        "images": None,
                                    },
                                    "error": f"\n\nError: {error_msg}",
                                    "done": False,
                                }
                                yield f"{json.dumps(error_data, ensure_ascii=False)}\n"

                                # Send final message to close the stream
                                final_data = {
                                    "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                    "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
                                "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                                "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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

                    return StreamingResponse(
                        stream_generator(),
                        media_type="application/x-ndjson",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Content-Type": "application/x-ndjson",
                            "X-Accel-Buffering": "no",  # Ensure proper handling of streaming responses in Nginx proxy
                        },
                    )
                else:
                    first_chunk_time = time.time_ns()

                    # Determine if the request is prefix with "/bypass" or from Open WebUI's session title and session keyword generation task
                    match_result = re.search(
                        r"\n<chat_history>\nUSER:", cleaned_query, re.MULTILINE
                    )
                    if match_result or mode == SearchMode.bypass:
                        if request.system:
                            self.rag.llm_model_kwargs["system_prompt"] = request.system

                        response_text = await self.rag.llm_model_func(
                            cleaned_query,
                            stream=False,
                            history_messages=conversation_history,
                            **self.rag.llm_model_kwargs,
                        )
                    else:
                        response_text = await self.rag.aquery(
                            cleaned_query, param=query_param
                        )

                    last_chunk_time = time.time_ns()

                    if not response_text:
                        response_text = "No response generated"

                    completion_tokens = estimate_tokens(str(response_text))
                    total_time = last_chunk_time - start_time
                    prompt_eval_time = first_chunk_time - start_time
                    eval_time = last_chunk_time - first_chunk_time

                    return {
                        "model": self.ollama_server_infos.LIGHTRAG_MODEL,
                        "created_at": self.ollama_server_infos.LIGHTRAG_CREATED_AT,
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
            except Exception as e:
                logger.error(f"Ollama chat error: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
