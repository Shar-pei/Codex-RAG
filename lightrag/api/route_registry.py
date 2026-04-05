from __future__ import annotations

from fastapi import FastAPI

from lightrag.api.app_auth_routes import create_auth_router
from lightrag.api.app_health_routes import create_health_router
from lightrag.api.app_route_context import (
    RouteRegistryContext,
    build_version_payload,
    resolve_auth_handler,
)
from lightrag.api.app_shell_routes import create_app_shell_router
from lightrag.api.app_static_mounts import register_static_mounts
from lightrag.api.routers.document_routes import (
    create_document_routes,
)
from lightrag.api.routers.graph_routes import create_graph_routes
from lightrag.api.routers.ollama_api import create_ollama_router
from lightrag.api.routers.query_routes import create_query_routes
from lightrag.api.utils_api import get_combined_auth_dependency


def register_app_routes(app: FastAPI, context: RouteRegistryContext) -> None:
    combined_auth = get_combined_auth_dependency(context.api_key)
    auth_handler = resolve_auth_handler(context)

    app.include_router(
        create_document_routes(
            context.rag,
            context.doc_manager,
            context.api_key,
        )
    )
    app.include_router(
        create_query_routes(context.rag, context.api_key, context.args.top_k)
    )
    app.include_router(create_graph_routes(context.rag, context.api_key))

    app.include_router(
        create_ollama_router(
            context.rag,
            top_k=context.args.top_k,
            api_key=context.api_key,
        ),
        prefix="/api",
    )
    version_payload = build_version_payload(context)
    app.include_router(create_auth_router(auth_handler, version_payload))
    app.include_router(
        create_health_router(
            context=context,
            combined_auth=combined_auth,
            auth_handler=auth_handler,
            version_payload=version_payload,
        )
    )
    app.include_router(create_app_shell_router(app, context.webui_assets_exist))
    register_static_mounts(app, webui_assets_exist=context.webui_assets_exist)
