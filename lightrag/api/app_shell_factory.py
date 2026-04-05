from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from lightrag.api.app_cors import configure_cors
from lightrag.api.app_lifespan import create_app_lifespan
from lightrag.api.query_validation_handlers import (
    create_query_validation_exception_handler,
)


def build_app_shell(
    app_runtime,
    startup_state,
    args,
    app_kwargs,
    cors_origins,
    app_factory=FastAPI,
    lifespan_factory=create_app_lifespan,
    validation_handler_factory=create_query_validation_exception_handler,
    cors_configurer=configure_cors,
    route_context_builder=None,
    route_registrar=None,
):
    """Assemble the FastAPI app shell around the prepared runtime state."""
    if route_context_builder is None:
        from lightrag.api.app_route_context import build_route_registry_context

        route_context_builder = build_route_registry_context

    if route_registrar is None:
        from lightrag.api.route_registry import register_app_routes

        route_registrar = register_app_routes

    app = app_factory(lifespan=lifespan_factory(app_runtime.rag), **app_kwargs)
    app.exception_handler(RequestValidationError)(validation_handler_factory())
    cors_configurer(app, cors_origins)
    route_registrar(
        app,
        route_context_builder(
            rag=app_runtime.rag,
            startup_state=startup_state,
            args=args,
            rerank_enabled=app_runtime.rerank_enabled,
        ),
    )
    return app
