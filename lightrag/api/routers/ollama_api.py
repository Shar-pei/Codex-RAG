from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from lightrag import LightRAG
from lightrag.api.routers.ollama_chat_handlers import (
    execute_chat_request as _execute_chat_request,
    iter_chat_stream_payloads as _iter_chat_stream_payloads,
)
from lightrag.api.routers.ollama_generate_handlers import (
    execute_generate_request as _execute_generate_request,
    iter_generate_stream_payloads as _iter_generate_stream_payloads,
)
from lightrag.api.routers.ollama_metadata_endpoints import (
    build_ollama_running_models_response as _build_ollama_running_models_response,
    build_ollama_tags_response as _build_ollama_tags_response,
    build_ollama_version_response as _build_ollama_version_response,
)
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
build_ollama_version_response = _build_ollama_version_response
build_ollama_tags_response = _build_ollama_tags_response
build_ollama_running_models_response = _build_ollama_running_models_response
execute_generate_request = _execute_generate_request
iter_generate_stream_payloads = _iter_generate_stream_payloads
execute_chat_request = _execute_chat_request
iter_chat_stream_payloads = _iter_chat_stream_payloads


def _raise_ollama_route_error(route_name: str, exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    logger.error(f"Ollama {route_name} error: {str(exc)}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc)) from exc


def create_ollama_router(
    rag: LightRAG,
    top_k: int = 60,
    api_key: Optional[str] = None,
) -> APIRouter:
    router = APIRouter(tags=["ollama"])
    server_infos = rag.ollama_server_infos
    combined_auth = get_combined_auth_dependency(api_key)

    @router.get("/version", dependencies=[Depends(combined_auth)])
    async def get_version():
        """Get Ollama version information"""
        return build_ollama_version_response()

    @router.get("/tags", dependencies=[Depends(combined_auth)])
    async def get_tags():
        """Return available models acting as an Ollama server"""
        return build_ollama_tags_response(server_infos)

    @router.get("/ps", dependencies=[Depends(combined_auth)])
    async def get_running_models():
        """List Running Models - returns currently running models"""
        return build_ollama_running_models_response(server_infos)

    @router.post("/generate", dependencies=[Depends(combined_auth)], include_in_schema=True)
    async def generate(raw_request: Request):
        """Handle generate completion requests acting as an Ollama model
        For compatibility purpose, the request is not processed by LightRAG,
        and will be handled by underlying LLM model.
        Supports both application/json and application/octet-stream Content-Types.
        """
        try:
            request = await parse_request_body(raw_request, OllamaGenerateRequest)
            return await execute_generate_request(rag, server_infos, request)
        except Exception as exc:
            _raise_ollama_route_error("generate", exc)

    @router.post("/chat", dependencies=[Depends(combined_auth)], include_in_schema=True)
    async def chat(raw_request: Request):
        """Process chat completion requests by acting as an Ollama model.
        Routes user queries through LightRAG by selecting query mode based on query prefix.
        Detects and forwards OpenWebUI session-related requests (for meta data generation task) directly to LLM.
        Supports both application/json and application/octet-stream Content-Types.
        """
        try:
            request = await parse_request_body(raw_request, OllamaChatRequest)
            return await execute_chat_request(rag, server_infos, request, top_k)
        except Exception as exc:
            _raise_ollama_route_error("chat", exc)

    return router


class OllamaAPI:
    def __init__(self, rag: LightRAG, top_k: int = 60, api_key: Optional[str] = None):
        self.rag = rag
        self.ollama_server_infos = rag.ollama_server_infos
        self.top_k = top_k
        self.api_key = api_key
        self.router = create_ollama_router(rag, top_k=top_k, api_key=api_key)
