from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import app_composition


def _args(**overrides):
    defaults = {
        "log_level": "DEBUG",
        "verbose": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_app_composition_orders_helpers_and_forwards_state():
    args = _args()
    startup_state = SimpleNamespace(api_key="api-key")
    runtime_dependencies = SimpleNamespace(name="runtime-deps")
    app_runtime = SimpleNamespace(name="app-runtime")
    logger_levels = []
    verbose_flags = []
    calls = []

    def fake_startup_state_builder(actual_args, *, api_version):
        calls.append(("startup_state", actual_args, api_version))
        return startup_state

    def fake_runtime_dependencies_builder(actual_args):
        calls.append(("runtime_dependencies", actual_args))
        return runtime_dependencies

    def fake_app_kwargs_builder(*, api_key, api_version):
        calls.append(("app_kwargs", api_key, api_version))
        return {"title": "LightRAG", "version": api_version}

    def fake_app_runtime_builder(actual_args, actual_runtime_dependencies):
        calls.append(("app_runtime", actual_args, actual_runtime_dependencies))
        return app_runtime

    def fake_app_shell_builder(**kwargs):
        calls.append(("app_shell", kwargs))
        return "app-instance"

    runtime_logger = SimpleNamespace(
        setLevel=lambda level: logger_levels.append(level),
    )

    app = app_composition.build_app_composition(
        args=args,
        api_version="1.2.3",
        cors_origins=["https://example.com"],
        startup_state_builder=fake_startup_state_builder,
        runtime_dependencies_builder=fake_runtime_dependencies_builder,
        app_kwargs_builder=fake_app_kwargs_builder,
        app_runtime_builder=fake_app_runtime_builder,
        app_shell_builder=fake_app_shell_builder,
        runtime_logger=runtime_logger,
        verbose_debug_setter=lambda enabled: verbose_flags.append(enabled),
    )

    assert app == "app-instance"
    assert logger_levels == ["DEBUG"]
    assert verbose_flags == [True]
    assert calls == [
        ("startup_state", args, "1.2.3"),
        ("runtime_dependencies", args),
        ("app_kwargs", "api-key", "1.2.3"),
        ("app_runtime", args, runtime_dependencies),
        (
            "app_shell",
            {
                "app_runtime": app_runtime,
                "startup_state": startup_state,
                "args": args,
                "app_kwargs": {"title": "LightRAG", "version": "1.2.3"},
                "cors_origins": ["https://example.com"],
            },
        ),
    ]


def test_build_app_composition_preserves_non_verbose_false_flag():
    verbose_flags = []

    app_composition.build_app_composition(
        args=_args(log_level="INFO", verbose=False),
        api_version="1.2.3",
        cors_origins=[],
        startup_state_builder=lambda actual_args, *, api_version: SimpleNamespace(
            api_key=None
        ),
        runtime_dependencies_builder=lambda actual_args: "runtime-dependencies",
        app_kwargs_builder=lambda *, api_key, api_version: {},
        app_runtime_builder=lambda actual_args, actual_runtime_dependencies: "runtime",
        app_shell_builder=lambda **kwargs: "app",
        runtime_logger=SimpleNamespace(setLevel=lambda level: None),
        verbose_debug_setter=lambda enabled: verbose_flags.append(enabled),
    )

    assert verbose_flags == [False]
