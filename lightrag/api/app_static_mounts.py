from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lightrag.utils import logger


class SmartStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        normalized_path = path.replace("\\", "/")

        is_html = normalized_path.endswith(".html") or response.media_type == "text/html"
        if is_html:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif normalized_path.startswith("assets/") or "/assets/" in normalized_path:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        if normalized_path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        elif normalized_path.endswith(".css"):
            response.headers["Content-Type"] = "text/css"

        return response


def register_static_mounts(
    app: FastAPI,
    *,
    webui_assets_exist: bool,
    base_dir: Path | None = None,
) -> None:
    if base_dir is None:
        base_dir = Path(__file__).parent

    swagger_static_dir = base_dir / "static" / "swagger-ui"
    if swagger_static_dir.exists():
        app.mount(
            "/static/swagger-ui",
            StaticFiles(directory=swagger_static_dir),
            name="swagger-ui-static",
        )

    if webui_assets_exist:
        static_dir = base_dir / "webui"
        static_dir.mkdir(exist_ok=True)
        app.mount(
            "/webui",
            SmartStaticFiles(directory=static_dir, html=True, check_dir=True),
            name="webui",
        )
        logger.info("WebUI assets mounted at /webui")
    else:
        logger.info("WebUI assets not available, /webui route not mounted")
