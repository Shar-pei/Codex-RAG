from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightrag.api.app_auth_routes import create_auth_router


def _auth_handler(accounts: dict[str, str] | None = None) -> SimpleNamespace:
    accounts = accounts or {}
    return SimpleNamespace(
        accounts=accounts,
        create_token=lambda **kwargs: f"token-for-{kwargs['username']}",
    )


def _version_payload() -> dict[str, str]:
    return {
        "core_version": "1.0.0",
        "api_version": "2.0.0",
        "webui_title": "LightRAG",
        "webui_description": "API",
    }


def test_create_auth_router_returns_fresh_router_each_time():
    router_one = create_auth_router(_auth_handler(), _version_payload())
    router_two = create_auth_router(_auth_handler(), _version_payload())

    assert router_one is not router_two
    assert [route.path for route in router_one.routes] == ["/auth-status", "/login"]
    assert [route.path for route in router_two.routes] == ["/auth-status", "/login"]


def test_auth_router_guest_mode_reuses_shared_guest_payload():
    app = FastAPI()
    app.include_router(create_auth_router(_auth_handler(), _version_payload()))
    client = TestClient(app)

    auth_status = client.get("/auth-status")
    assert auth_status.status_code == 200
    assert auth_status.json()["auth_configured"] is False
    assert auth_status.json()["access_token"] == "token-for-guest"
    assert auth_status.json()["auth_mode"] == "disabled"

    login = client.post("/login", data={"username": "ignored", "password": "ignored"})
    assert login.status_code == 200
    assert login.json()["access_token"] == "token-for-guest"
    assert login.json()["auth_mode"] == "disabled"


def test_auth_router_enabled_mode_validates_credentials():
    app = FastAPI()
    app.include_router(
        create_auth_router(_auth_handler({"alice": "secret"}), _version_payload())
    )
    client = TestClient(app)

    auth_status = client.get("/auth-status")
    assert auth_status.status_code == 200
    assert auth_status.json()["auth_configured"] is True
    assert auth_status.json()["auth_mode"] == "enabled"

    bad_login = client.post("/login", data={"username": "alice", "password": "wrong"})
    assert bad_login.status_code == 401
    assert bad_login.json()["detail"] == "Incorrect credentials"

    good_login = client.post("/login", data={"username": "alice", "password": "secret"})
    assert good_login.status_code == 200
    assert good_login.json()["access_token"] == "token-for-alice"
    assert good_login.json()["auth_mode"] == "enabled"
