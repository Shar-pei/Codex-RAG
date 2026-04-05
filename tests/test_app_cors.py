from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lightrag.api.app_cors import configure_cors, get_cors_origins


def test_get_cors_origins_preserves_wildcard_contract():
    assert get_cors_origins("*") == ["*"]


def test_get_cors_origins_splits_and_trims_comma_separated_values():
    assert get_cors_origins(" https://a.example,https://b.example , http://localhost:3000 ") == [
        "https://a.example",
        "https://b.example",
        "http://localhost:3000",
    ]


def test_configure_cors_registers_middleware_with_expected_origins():
    app = FastAPI()
    configure_cors(app, "https://a.example, https://b.example")

    assert len(app.user_middleware) == 1
    middleware = app.user_middleware[0]
    assert middleware.cls is CORSMiddleware
    assert middleware.kwargs["allow_origins"] == [
        "https://a.example",
        "https://b.example",
    ]
    assert middleware.kwargs["allow_credentials"] is True
    assert middleware.kwargs["allow_methods"] == ["*"]
    assert middleware.kwargs["allow_headers"] == ["*"]
