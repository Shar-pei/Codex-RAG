from __future__ import annotations

from lightrag.api import process_entrypoint


def test_run_process_entrypoint_short_circuits_under_gunicorn():
    calls = []
    messages = []

    result = process_entrypoint.run_process_entrypoint(
        global_args="global-args",
        app_builder=lambda args: calls.append(("app_builder", args)),
        dependency_checker=lambda: calls.append(("dependency_checker",)),
        logging_configurer=lambda: calls.append(("logging_configurer",)),
        uvicorn_mode_updater=lambda: calls.append(("uvicorn_mode_updater",)),
        env_checker=lambda: calls.append(("env_checker",)),
        splash_displayer=lambda args: calls.append(("splash_displayer", args)),
        initialize_config_func=lambda: calls.append(("initialize_config",)),
        startup_runner=lambda **kwargs: calls.append(("startup_runner", kwargs)),
        environ={"GUNICORN_CMD_ARGS": "workers=2"},
        printer=lambda message: messages.append(message),
    )

    assert result is None
    assert calls == [("initialize_config",)]
    assert messages == ["Running under Gunicorn - worker management handled by Gunicorn"]


def test_run_process_entrypoint_initializes_then_delegates_to_startup_runner():
    calls = []

    def fake_startup_runner(**kwargs):
        calls.append(("startup_runner", kwargs))
        return "startup-result"

    result = process_entrypoint.run_process_entrypoint(
        global_args="global-args",
        app_builder="create-app",
        dependency_checker="dependency-checker",
        logging_configurer="logging-configurer",
        uvicorn_mode_updater="uvicorn-updater",
        env_checker="env-checker",
        splash_displayer="splash-displayer",
        initialize_config_func=lambda: calls.append(("initialize_config",)),
        startup_runner=fake_startup_runner,
        environ={},
        printer=lambda message: calls.append(("print", message)),
    )

    assert result == "startup-result"
    assert calls == [
        ("initialize_config",),
        (
            "startup_runner",
            {
                "args": "global-args",
                "app_builder": "create-app",
                "dependency_checker": "dependency-checker",
                "logging_configurer": "logging-configurer",
                "uvicorn_mode_updater": "uvicorn-updater",
                "env_checker": "env-checker",
                "splash_displayer": "splash-displayer",
            },
        ),
    ]
