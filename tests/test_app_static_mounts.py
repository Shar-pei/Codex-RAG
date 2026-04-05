from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightrag.api.app_static_mounts import SmartStaticFiles, register_static_mounts


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _scratch_dir() -> Path:
    scratch = Path.cwd() / ".tmp" / "codex-static-tests" / uuid.uuid4().hex
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def test_smart_static_files_sets_expected_cache_headers():
    scratch = _scratch_dir()
    try:
        webui_dir = scratch / "webui"
        _write_file(webui_dir / "index.html", "<html>home</html>")
        _write_file(webui_dir / "assets" / "app.js", "console.log('hi');")
        _write_file(webui_dir / "styles.css", "body {}")

        app = FastAPI()
        app.mount(
            "/webui", SmartStaticFiles(directory=webui_dir, html=True, check_dir=True)
        )
        client = TestClient(app)

        html_response = client.get("/webui/index.html")
        assert html_response.status_code == 200
        assert (
            html_response.headers["cache-control"]
            == "no-cache, no-store, must-revalidate"
        )
        assert html_response.headers["pragma"] == "no-cache"
        assert html_response.headers["expires"] == "0"

        asset_response = client.get("/webui/assets/app.js")
        assert asset_response.status_code == 200
        assert (
            asset_response.headers["cache-control"]
            == "public, max-age=31536000, immutable"
        )
        assert asset_response.headers["content-type"].startswith(
            "application/javascript"
        )

        css_response = client.get("/webui/styles.css")
        assert css_response.status_code == 200
        assert css_response.headers["content-type"].startswith("text/css")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_register_static_mounts_mounts_swagger_and_webui_assets():
    scratch = _scratch_dir()
    try:
        swagger_dir = scratch / "static" / "swagger-ui"
        webui_dir = scratch / "webui"
        _write_file(swagger_dir / "swagger-ui.css", "body {}")
        _write_file(webui_dir / "index.html", "<html>webui</html>")

        app = FastAPI()
        register_static_mounts(app, webui_assets_exist=True, base_dir=scratch)

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert "/static/swagger-ui" in paths
        assert "/webui" in paths

        client = TestClient(app)
        swagger_response = client.get("/static/swagger-ui/swagger-ui.css")
        assert swagger_response.status_code == 200

        webui_response = client.get("/webui/index.html")
        assert webui_response.status_code == 200
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_register_static_mounts_skips_webui_mount_when_assets_are_disabled():
    scratch = _scratch_dir()
    try:
        swagger_dir = scratch / "static" / "swagger-ui"
        _write_file(swagger_dir / "swagger-ui.css", "body {}")

        app = FastAPI()
        register_static_mounts(app, webui_assets_exist=False, base_dir=scratch)

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert "/static/swagger-ui" in paths
        assert "/webui" not in paths
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
