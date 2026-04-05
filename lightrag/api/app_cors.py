from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def get_cors_origins(origins_str: str) -> list[str]:
    """Parse the configured CORS origins string into FastAPI middleware format."""
    if origins_str == "*":
        return ["*"]
    return [origin.strip() for origin in origins_str.split(",")]


def configure_cors(app: FastAPI, origins_str: str) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(origins_str),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
