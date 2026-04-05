from __future__ import annotations


def build_app_kwargs(api_key: str | None, api_version: str) -> dict:
    """Build the static FastAPI configuration for the LightRAG server."""

    base_description = "Providing API for LightRAG core, Web UI and Ollama Model Emulation"
    swagger_description = (
        base_description
        + (" (API-Key Enabled)" if api_key else "")
        + "\n\n[View ReDoc documentation](/redoc)"
    )

    return {
        "title": "LightRAG Server API",
        "description": swagger_description,
        "version": api_version,
        "openapi_url": "/openapi.json",
        "docs_url": None,
        "redoc_url": "/redoc",
        "swagger_ui_parameters": {
            "persistAuthorization": True,
            "tryItOutEnabled": True,
        },
    }
