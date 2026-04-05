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
            return build_ollama_version_response()

        @self.router.get("/tags", dependencies=[Depends(combined_auth)])
        async def get_tags():
            """Return available models acting as an Ollama server"""
            return build_ollama_tags_response(self.ollama_server_infos)

        @self.router.get("/ps", dependencies=[Depends(combined_auth)])
        async def get_running_models():
            """List Running Models - returns currently running models"""
            return build_ollama_running_models_response(self.ollama_server_infos)

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
                request = await parse_request_body(raw_request, OllamaGenerateRequest)
                return await execute_generate_request(
                    self.rag, self.ollama_server_infos, request
                )
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
                request = await parse_request_body(raw_request, OllamaChatRequest)
                return await execute_chat_request(
                    self.rag,
                    self.ollama_server_infos,
                    request,
                    self.top_k,
                )
            except Exception as e:
                logger.error(f"Ollama chat error: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
