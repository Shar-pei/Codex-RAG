from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import RedirectResponse


def create_app_shell_router(app: FastAPI, webui_assets_exist: bool) -> APIRouter:
    router = APIRouter()

    @router.get("/docs", include_in_schema=False)
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

    @router.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @router.get("/")
    async def redirect_to_webui():
        if webui_assets_exist:
            return RedirectResponse(url="/webui")
        return RedirectResponse(url="/docs")

    if not webui_assets_exist:

        @router.get("/webui")
        @router.get("/webui/")
        async def webui_redirect_to_docs():
            return RedirectResponse(url="/docs")

    return router
