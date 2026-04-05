from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lightrag import LightRAG, __version__ as core_version
from lightrag.api.routers.document_routes import DocumentManager


@dataclass
class RouteRegistryContext:
    rag: LightRAG
    doc_manager: DocumentManager
    api_key: str | None
    args: Any
    api_version_display: str
    webui_assets_exist: bool
    webui_title: str | None
    webui_description: str | None
    rerank_enabled: bool
    auth_handler: Any | None = None


def build_version_payload(context: RouteRegistryContext) -> dict[str, Any]:
    return {
        "core_version": core_version,
        "api_version": context.api_version_display,
        "webui_title": context.webui_title,
        "webui_description": context.webui_description,
    }


def resolve_auth_handler(context: RouteRegistryContext):
    if context.auth_handler is not None:
        return context.auth_handler

    from lightrag.api.auth import auth_handler

    return auth_handler
