from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightrag.api.app_shell_routes import create_app_shell_router


def _app() -> FastAPI:
    app = FastAPI(title="LightRAG")
    app.swagger_ui_parameters = {"deepLinking": True}
    return app


def test_create_app_shell_router_returns_a_fresh_router_each_time():
    app = _app()
    router_one = create_app_shell_router(app, webui_assets_exist=True)
    router_two = create_app_shell_router(app, webui_assets_exist=True)

    assert router_one is not router_two
    assert [route.path for route in router_one.routes] == [
        "/docs",
        "/docs/oauth2-redirect",
        "/",
    ]
    assert [route.path for route in router_two.routes] == [
        "/docs",
        "/docs/oauth2-redirect",
        "/",
    ]


def test_app_shell_router_redirects_root_to_webui_when_assets_exist():
    app = _app()
    app.include_router(create_app_shell_router(app, webui_assets_exist=True))
    client = TestClient(app)

    root_response = client.get("/", follow_redirects=False)
    assert root_response.status_code == 307
    assert root_response.headers["location"] == "/webui"

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text


def test_app_shell_router_adds_webui_fallback_when_assets_are_missing():
    app = _app()
    app.include_router(create_app_shell_router(app, webui_assets_exist=False))
    client = TestClient(app)

    root_response = client.get("/", follow_redirects=False)
    assert root_response.status_code == 307
    assert root_response.headers["location"] == "/docs"

    webui_response = client.get("/webui", follow_redirects=False)
    assert webui_response.status_code == 307
    assert webui_response.headers["location"] == "/docs"

    oauth_response = client.get("/docs/oauth2-redirect")
    assert oauth_response.status_code == 200
