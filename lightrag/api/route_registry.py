from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from lightrag import LightRAG, __version__ as core_version
from lightrag.api.app_auth_routes import create_auth_router
from lightrag.api.app_health_routes import create_health_router
from lightrag.api.routers.document_routes import (
    DocumentManager,
    create_document_routes,
)
from lightrag.api.routers.graph_routes import create_graph_routes
from lightrag.api.routers.ollama_api import create_ollama_router
from lightrag.api.routers.query_routes import create_query_routes
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.utils import logger


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


class SmartStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        is_html = path.endswith(".html") or response.media_type == "text/html"
        if is_html:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif "/assets/" in path:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        elif path.endswith(".css"):
            response.headers["Content-Type"] = "text/css"

        return response


def _build_version_payload(context: RouteRegistryContext) -> dict[str, Any]:
    return {
        "core_version": core_version,
        "api_version": context.api_version_display,
        "webui_title": context.webui_title,
        "webui_description": context.webui_description,
    }


def _get_auth_handler(context: RouteRegistryContext):
    if context.auth_handler is not None:
        return context.auth_handler

    from lightrag.api.auth import auth_handler

    return auth_handler


def register_app_routes(app: FastAPI, context: RouteRegistryContext) -> None:
    combined_auth = get_combined_auth_dependency(context.api_key)
    auth_handler = _get_auth_handler(context)

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
    version_payload = _build_version_payload(context)
    app.include_router(create_auth_router(auth_handler, version_payload))
    app.include_router(
        create_health_router(
            context=context,
            combined_auth=combined_auth,
            auth_handler=auth_handler,
            version_payload=version_payload,
        )
    )

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui/swagger-ui.css",
            swagger_favicon_url="/static/swagger-ui/favicon-32x32.png",
            swagger_ui_parameters=app.swagger_ui_parameters,
        )

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/")
    async def redirect_to_webui():
        if context.webui_assets_exist:
            return RedirectResponse(url="/webui")
        return RedirectResponse(url="/docs")

    swagger_static_dir = Path(__file__).parent / "static" / "swagger-ui"
    if swagger_static_dir.exists():
        app.mount(
            "/static/swagger-ui",
            StaticFiles(directory=swagger_static_dir),
            name="swagger-ui-static",
        )

    if context.webui_assets_exist:
        static_dir = Path(__file__).parent / "webui"
        static_dir.mkdir(exist_ok=True)
        app.mount(
            "/webui",
            SmartStaticFiles(directory=static_dir, html=True, check_dir=True),
            name="webui",
        )
        logger.info("WebUI assets mounted at /webui")
    else:
        logger.info("WebUI assets not available, /webui route not mounted")

        @app.get("/webui")
        @app.get("/webui/")
        async def webui_redirect_to_docs():
            return RedirectResponse(url="/docs")
