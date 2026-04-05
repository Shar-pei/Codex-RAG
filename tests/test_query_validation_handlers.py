from __future__ import annotations

import asyncio

from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from lightrag.api.query_validation_handlers import (
    create_query_validation_exception_handler,
)


def _request(path: str) -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope, receive)


def _validation_error():
    return RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("body", "query"),
                "msg": "Field required",
                "input": {},
            }
        ]
    )


def test_query_data_validation_handler_returns_data_endpoint_contract():
    handler = create_query_validation_exception_handler()

    response = asyncio.run(handler(_request("/query/data"), _validation_error()))

    assert response.status_code == 400
    assert response.body == (
        b'{"status":"failure","message":"Validation error: body -> query: '
        b'Field required","data":{},"metadata":{}}'
    )


def test_query_data_validation_handler_falls_back_to_default_422_for_other_paths():
    handler = create_query_validation_exception_handler()

    response = asyncio.run(handler(_request("/documents"), _validation_error()))

    assert response.status_code == 422
    assert b'"detail"' in response.body
