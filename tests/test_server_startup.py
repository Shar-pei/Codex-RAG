from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import server_startup


def _args(**overrides):
    defaults = {
        "host": "127.0.0.1",
        "port": 9621,
        "ssl": False,
        "ssl_certfile": None,
        "ssl_keyfile": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_run_server_startup_orders_single_process_boot_and_forwards_uvicorn_config():
    args = _args(ssl=True, ssl_certfile="cert.pem", ssl_keyfile="key.pem")
    calls = []
    uvicorn_calls = []

    app = server_startup.run_server_startup(
        args=args,
        app_builder=lambda actual_args: calls.append(("app_builder", actual_args))
        or "app-instance",
        dependency_checker=lambda: calls.append(("dependency_checker",)),
        logging_configurer=lambda: calls.append(("logging_configurer",)),
        uvicorn_mode_updater=lambda: calls.append(("uvicorn_mode_updater",)),
        env_checker=lambda: calls.append(("env_checker",)) or True,
        splash_displayer=lambda actual_args: calls.append(("splash_displayer", actual_args)),
        freeze_support_func=lambda: calls.append(("freeze_support",)),
        uvicorn_runner=lambda **kwargs: uvicorn_calls.append(kwargs),
        exit_func=lambda code: calls.append(("exit", code)),
    )

    assert app == "app-instance"
    assert calls == [
        ("env_checker",),
        ("dependency_checker",),
        ("freeze_support",),
        ("logging_configurer",),
        ("uvicorn_mode_updater",),
        ("splash_displayer", args),
        ("app_builder", args),
    ]
    assert uvicorn_calls == [
        {
            "app": "app-instance",
            "host": "127.0.0.1",
            "port": 9621,
            "log_config": None,
            "ssl_certfile": "cert.pem",
            "ssl_keyfile": "key.pem",
        }
    ]


def test_run_server_startup_exits_early_when_env_check_fails():
    calls = []

    app = server_startup.run_server_startup(
        args=_args(),
        app_builder=lambda actual_args: calls.append(("app_builder", actual_args)),
        dependency_checker=lambda: calls.append(("dependency_checker",)),
        logging_configurer=lambda: calls.append(("logging_configurer",)),
        uvicorn_mode_updater=lambda: calls.append(("uvicorn_mode_updater",)),
        env_checker=lambda: False,
        splash_displayer=lambda actual_args: calls.append(("splash_displayer", actual_args)),
        freeze_support_func=lambda: calls.append(("freeze_support",)),
        uvicorn_runner=lambda **kwargs: calls.append(("uvicorn_runner", kwargs)),
        exit_func=lambda code: calls.append(("exit", code)),
    )

    assert app is None
    assert calls == [("exit", 1)]
