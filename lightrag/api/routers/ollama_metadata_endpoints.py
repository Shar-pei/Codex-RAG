from __future__ import annotations

from lightrag.api.routers.ollama_models import (
    OllamaPsResponse,
    OllamaTagResponse,
    OllamaVersionResponse,
)


def build_ollama_version_response() -> OllamaVersionResponse:
    return OllamaVersionResponse(version="0.9.3")


def build_ollama_tags_response(server_infos) -> OllamaTagResponse:
    return OllamaTagResponse(
        models=[
            {
                "name": server_infos.LIGHTRAG_MODEL,
                "model": server_infos.LIGHTRAG_MODEL,
                "modified_at": server_infos.LIGHTRAG_CREATED_AT,
                "size": server_infos.LIGHTRAG_SIZE,
                "digest": server_infos.LIGHTRAG_DIGEST,
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": server_infos.LIGHTRAG_NAME,
                    "families": [server_infos.LIGHTRAG_NAME],
                    "parameter_size": "13B",
                    "quantization_level": "Q4_0",
                },
            }
        ]
    )


def build_ollama_running_models_response(server_infos) -> OllamaPsResponse:
    return OllamaPsResponse(
        models=[
            {
                "name": server_infos.LIGHTRAG_MODEL,
                "model": server_infos.LIGHTRAG_MODEL,
                "size": server_infos.LIGHTRAG_SIZE,
                "digest": server_infos.LIGHTRAG_DIGEST,
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "7.2B",
                    "quantization_level": "Q4_0",
                },
                "expires_at": "2050-12-31T14:38:31.83753-07:00",
                "size_vram": server_infos.LIGHTRAG_SIZE,
            }
        ]
    )
