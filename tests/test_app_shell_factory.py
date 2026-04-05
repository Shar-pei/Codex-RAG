from __future__ import annotations

from types import SimpleNamespace

from fastapi.exceptions import RequestValidationError

from lightrag.api import app_shell_factory


class FakeApp:
    def __init__(self, *, lifespan, **kwargs):
        self.lifespan = lifespan
        self.kwargs = kwargs
        self.exception_handlers = []

    def exception_handler(self, exc_cls):
        def register(handler):
            self.exception_handlers.append((exc_cls, handler))
            return handler

        return register


def test_build_app_shell_wires_lifespan_validation_cors_and_routes():
    app_runtime = SimpleNamespace(rag="rag-instance", rerank_enabled=True)
    startup_state = SimpleNamespace(doc_manager="doc-manager")
    args = SimpleNamespace()
    app_kwargs = {"title": "LightRAG", "version": "1.0.0"}
    calls = []

    def fake_app_factory(**kwargs):
        calls.append(("app_factory", kwargs))
        return FakeApp(**kwargs)

    def fake_lifespan_factory(rag):
        calls.append(("lifespan_factory", rag))
        return "lifespan"

    def fake_validation_handler_factory():
        calls.append(("validation_handler_factory",))
        return "validation-handler"

    def fake_cors_configurer(app, cors_origins):
        calls.append(("cors_configurer", app, cors_origins))

    def fake_route_context_builder(**kwargs):
        calls.append(("route_context_builder", kwargs))
        return "route-context"

    def fake_route_registrar(app, context):
        calls.append(("route_registrar", app, context))

    app = app_shell_factory.build_app_shell(
        app_runtime=app_runtime,
        startup_state=startup_state,
        args=args,
        app_kwargs=app_kwargs,
        cors_origins=["https://example.com"],
        app_factory=fake_app_factory,
        lifespan_factory=fake_lifespan_factory,
        validation_handler_factory=fake_validation_handler_factory,
        cors_configurer=fake_cors_configurer,
        route_context_builder=fake_route_context_builder,
        route_registrar=fake_route_registrar,
    )

    assert isinstance(app, FakeApp)
    assert app.lifespan == "lifespan"
    assert app.kwargs == app_kwargs
    assert app.exception_handlers == [
        (RequestValidationError, "validation-handler")
    ]
    assert calls == [
        ("lifespan_factory", "rag-instance"),
        ("app_factory", {"lifespan": "lifespan", **app_kwargs}),
        ("validation_handler_factory",),
        ("cors_configurer", app, ["https://example.com"]),
        (
            "route_context_builder",
            {
                "rag": "rag-instance",
                "startup_state": startup_state,
                "args": args,
                "rerank_enabled": True,
            },
        ),
        ("route_registrar", app, "route-context"),
    ]


def test_build_app_shell_forwards_disabled_rerank_state_to_context_builder():
    rerank_flags = []

    app_shell_factory.build_app_shell(
        app_runtime=SimpleNamespace(rag="rag-instance", rerank_enabled=False),
        startup_state=SimpleNamespace(),
        args=SimpleNamespace(),
        app_kwargs={},
        cors_origins=[],
        app_factory=lambda **kwargs: FakeApp(**kwargs),
        lifespan_factory=lambda rag: "lifespan",
        validation_handler_factory=lambda: "validation-handler",
        cors_configurer=lambda app, cors_origins: None,
        route_context_builder=lambda **kwargs: rerank_flags.append(
            kwargs["rerank_enabled"]
        )
        or "route-context",
        route_registrar=lambda app, context: None,
    )

    assert rerank_flags == [False]
