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


def build_route_registry_context(
    rag: LightRAG,
    startup_state,
    args: Any,
    rerank_enabled: bool,
    auth_handler: Any | None = None,
) -> RouteRegistryContext:
    context = RouteRegistryContext(
        rag=rag,
        doc_manager=startup_state.doc_manager,
        api_key=startup_state.api_key,
        args=args,
        api_version_display=startup_state.api_version_display,
        webui_assets_exist=startup_state.webui_assets_exist,
        webui_title=startup_state.webui_title,
        webui_description=startup_state.webui_description,
        rerank_enabled=rerank_enabled,
        auth_handler=auth_handler,
    )
    if context.auth_handler is None:
        context.auth_handler = resolve_auth_handler(context)
    return context
