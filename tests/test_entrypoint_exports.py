from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import config as api_config
from lightrag.api import entrypoint_exports


def test_create_app_forwards_to_bound_facade_with_global_cors_origins(monkeypatch):
    calls = []

    monkeypatch.setattr(
        entrypoint_exports,
        "global_args",
        SimpleNamespace(cors_origins=["https://example.com"]),
    )
    monkeypatch.setattr(
        entrypoint_exports,
        "create_app_with_bindings",
        lambda **kwargs: calls.append(kwargs) or "app",
    )

    result = entrypoint_exports.create_app("args")

    assert result == "app"
    assert calls == [
        {
            "args": "args",
            "api_version": entrypoint_exports.__api_version__,
            "cors_origins": ["https://example.com"],
        }
    ]


def test_get_application_defaults_to_global_args(monkeypatch):
    default_args = object()
    calls = []

    monkeypatch.setattr(entrypoint_exports, "global_args", default_args)
    monkeypatch.setattr(
        entrypoint_exports,
        "create_app",
        lambda args: calls.append(args) or "app",
    )

    result = entrypoint_exports.get_application()

    assert result == "app"
    assert calls == [default_args]


def test_configure_logging_forwards_wrapper_bindings(monkeypatch):
    calls = []

    monkeypatch.setattr(
        entrypoint_exports,
        "configure_logging_with_bindings",
        lambda **kwargs: calls.append(kwargs),
    )

    entrypoint_exports.configure_logging()

    assert calls == [
        {
            "default_log_filename": entrypoint_exports.DEFAULT_LOG_FILENAME,
            "default_log_max_bytes": entrypoint_exports.DEFAULT_LOG_MAX_BYTES,
            "default_log_backup_count": entrypoint_exports.DEFAULT_LOG_BACKUP_COUNT,
            "get_env_value_func": entrypoint_exports.get_env_value,
            "logging_module": entrypoint_exports.logging,
            "os_module": entrypoint_exports.os,
            "printer": print,
        }
    ]


def test_check_and_install_dependencies_uses_bootstrap_package_manager(monkeypatch):
    calls = []

    monkeypatch.setattr(entrypoint_exports, "pm", "pm")
    monkeypatch.setattr(
        entrypoint_exports,
        "check_dependencies_with_bindings",
        lambda **kwargs: calls.append(kwargs),
    )

    entrypoint_exports.check_and_install_dependencies()

    assert calls == [{"package_manager": "pm"}]


def test_main_forwards_wrapper_exports_and_initialize_config(monkeypatch):
    calls = []

    monkeypatch.setattr(api_config, "initialize_config", "initialize-config")
    monkeypatch.setattr(entrypoint_exports, "global_args", "global-args")
    monkeypatch.setattr(entrypoint_exports, "create_app", "create-app")
    monkeypatch.setattr(
        entrypoint_exports,
        "check_and_install_dependencies",
        "dependency-checker",
    )
    monkeypatch.setattr(entrypoint_exports, "configure_logging", "logging-configurer")
    monkeypatch.setattr(
        entrypoint_exports,
        "update_uvicorn_mode_config",
        "uvicorn-updater",
    )
    monkeypatch.setattr(
        entrypoint_exports,
        "resolve_entrypoint_runtime_helpers",
        lambda: ("env-checker", "splash-displayer"),
    )
    monkeypatch.setattr(entrypoint_exports, "run_server_startup", "startup-runner")
    monkeypatch.setattr(
        entrypoint_exports,
        "run_main_with_bindings",
        lambda **kwargs: calls.append(kwargs),
    )

    entrypoint_exports.main()

    assert calls == [
        {
            "global_args": "global-args",
            "app_builder": "create-app",
            "dependency_checker": "dependency-checker",
            "logging_configurer": "logging-configurer",
            "uvicorn_mode_updater": "uvicorn-updater",
            "env_checker": "env-checker",
            "splash_displayer": "splash-displayer",
            "initialize_config_func": "initialize-config",
            "startup_runner": "startup-runner",
        }
    ]
