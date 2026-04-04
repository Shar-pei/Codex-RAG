from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from lightrag import LightRAG, __version__ as core_version
from lightrag.api.routers.document_routes import (
    DocumentManager,
    create_document_routes,
)
from lightrag.api.routers.graph_routes import create_graph_routes
from lightrag.api.routers.ollama_api import OllamaAPI
from lightrag.api.routers.query_routes import create_query_routes
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.kg.shared_storage import (
    cleanup_keyed_lock,
    get_default_workspace,
    get_namespace_data,
)
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


def _get_workspace_from_request(request: Request) -> str | None:
    workspace = request.headers.get("LIGHTRAG-WORKSPACE", "").strip()
    return workspace or None


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

    ollama_api = OllamaAPI(
        context.rag,
        top_k=context.args.top_k,
        api_key=context.api_key,
    )
    app.include_router(ollama_api.router, prefix="/api")

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

    @app.get("/auth-status")
    async def get_auth_status():
        if not auth_handler.accounts:
            guest_token = auth_handler.create_token(
                username="guest",
                role="guest",
                metadata={"auth_mode": "disabled"},
            )
            return {
                "auth_configured": False,
                "access_token": guest_token,
                "token_type": "bearer",
                "auth_mode": "disabled",
                "message": "Authentication is disabled. Using guest access.",
                **_build_version_payload(context),
            }

        return {
            "auth_configured": True,
            "auth_mode": "enabled",
            **_build_version_payload(context),
        }

    @app.post("/login")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        if not auth_handler.accounts:
            guest_token = auth_handler.create_token(
                username="guest",
                role="guest",
                metadata={"auth_mode": "disabled"},
            )
            return {
                "access_token": guest_token,
                "token_type": "bearer",
                "auth_mode": "disabled",
                "message": "Authentication is disabled. Using guest access.",
                **_build_version_payload(context),
            }

        username = form_data.username
        if auth_handler.accounts.get(username) != form_data.password:
            raise HTTPException(status_code=401, detail="Incorrect credentials")

        user_token = auth_handler.create_token(
            username=username,
            role="user",
            metadata={"auth_mode": "enabled"},
        )
        return {
            "access_token": user_token,
            "token_type": "bearer",
            "auth_mode": "enabled",
            **_build_version_payload(context),
        }

    @app.get(
        "/health",
        dependencies=[Depends(combined_auth)],
        summary="Get system health and configuration status",
        description="Returns comprehensive system status including WebUI availability, configuration, and operational metrics",
        response_description="System health status with configuration details",
        responses={
            200: {
                "description": "Successful response with system status",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "healthy",
                            "webui_available": True,
                            "working_directory": "/path/to/working/dir",
                            "input_directory": "/path/to/input/dir",
                            "configuration": {
                                "llm_binding": "openai",
                                "llm_model": "gpt-4",
                                "embedding_binding": "openai",
                                "embedding_model": "text-embedding-ada-002",
                                "workspace": "default",
                            },
                            "auth_mode": "enabled",
                            "pipeline_busy": False,
                            "core_version": "0.0.1",
                            "api_version": "0.0.1",
                        }
                    }
                },
            }
        },
    )
    async def get_status(request: Request):
        try:
            workspace = _get_workspace_from_request(request)
            default_workspace = get_default_workspace()
            if workspace is None:
                workspace = default_workspace
            pipeline_status = await get_namespace_data(
                "pipeline_status",
                workspace=workspace,
            )

            auth_mode = "enabled" if auth_handler.accounts else "disabled"
            keyed_lock_info = cleanup_keyed_lock()

            return {
                "status": "healthy",
                "webui_available": context.webui_assets_exist,
                "working_directory": str(context.args.working_dir),
                "input_directory": str(context.args.input_dir),
                "configuration": {
                    "llm_binding": context.args.llm_binding,
                    "llm_binding_host": context.args.llm_binding_host,
                    "llm_model": context.args.llm_model,
                    "embedding_binding": context.args.embedding_binding,
                    "embedding_binding_host": context.args.embedding_binding_host,
                    "embedding_model": context.args.embedding_model,
                    "summary_max_tokens": context.args.summary_max_tokens,
                    "summary_context_size": context.args.summary_context_size,
                    "kv_storage": context.args.kv_storage,
                    "doc_status_storage": context.args.doc_status_storage,
                    "graph_storage": context.args.graph_storage,
                    "vector_storage": context.args.vector_storage,
                    "enable_llm_cache_for_extract": context.args.enable_llm_cache_for_extract,
                    "enable_llm_cache": context.args.enable_llm_cache,
                    "workspace": default_workspace,
                    "max_graph_nodes": context.args.max_graph_nodes,
                    "enable_rerank": context.rerank_enabled,
                    "rerank_binding": context.args.rerank_binding,
                    "rerank_model": (
                        context.args.rerank_model if context.rerank_enabled else None
                    ),
                    "rerank_binding_host": (
                        context.args.rerank_binding_host
                        if context.rerank_enabled
                        else None
                    ),
                    "summary_language": context.args.summary_language,
                    "force_llm_summary_on_merge": context.args.force_llm_summary_on_merge,
                    "max_parallel_insert": context.args.max_parallel_insert,
                    "cosine_threshold": context.args.cosine_threshold,
                    "min_rerank_score": context.args.min_rerank_score,
                    "related_chunk_number": context.args.related_chunk_number,
                    "max_async": context.args.max_async,
                    "embedding_func_max_async": context.args.embedding_func_max_async,
                    "embedding_batch_num": context.args.embedding_batch_num,
                },
                "auth_mode": auth_mode,
                "pipeline_busy": pipeline_status.get("busy", False),
                "keyed_locks": keyed_lock_info,
                **_build_version_payload(context),
            }
        except Exception as exc:
            logger.error(f"Error getting health status: {str(exc)}")
            raise HTTPException(status_code=500, detail=str(exc))

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
