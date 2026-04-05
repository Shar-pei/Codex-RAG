from __future__ import annotations

from lightrag.api import entrypoint_facade


def test_create_app_with_bindings_forwards_api_version_and_cors_origins():
    calls = []

    result = entrypoint_facade.create_app_with_bindings(
        args="args",
        api_version="1.2.3",
        cors_origins=["https://example.com"],
        app_composer=lambda **kwargs: calls.append(kwargs) or "app",
    )

    assert result == "app"
    assert calls == [
        {
            "args": "args",
            "api_version": "1.2.3",
            "cors_origins": ["https://example.com"],
        }
    ]


def test_configure_logging_with_bindings_forwards_bound_logging_inputs():
    calls = []

    entrypoint_facade.configure_logging_with_bindings(
        default_log_filename="server.log",
        default_log_max_bytes=100,
        default_log_backup_count=2,
        get_env_value_func="get-env",
        logging_module="logging-module",
        os_module="os-module",
        printer="printer",
        logging_configurer=lambda **kwargs: calls.append(kwargs),
    )

    assert calls == [
        {
            "default_log_filename": "server.log",
            "default_log_max_bytes": 100,
            "default_log_backup_count": 2,
            "get_env_value_func": "get-env",
            "logging_module": "logging-module",
            "os_module": "os-module",
            "printer": "printer",
        }
    ]


def test_check_dependencies_with_bindings_uses_default_required_package_list():
    calls = []

    entrypoint_facade.check_dependencies_with_bindings(
        package_manager="pm",
        dependency_bootstrapper=lambda **kwargs: calls.append(kwargs),
    )

    assert calls == [
        {
            "required_packages": ["uvicorn", "tiktoken", "fastapi"],
            "package_manager": "pm",
        }
    ]


def test_run_main_with_bindings_forwards_entrypoint_dependencies():
    calls = []

    result = entrypoint_facade.run_main_with_bindings(
        global_args="global-args",
        app_builder="create-app",
        dependency_checker="dependency-checker",
        logging_configurer="logging-configurer",
        uvicorn_mode_updater="uvicorn-updater",
        env_checker="env-checker",
        splash_displayer="splash-displayer",
        initialize_config_func="initialize-config",
        startup_runner="startup-runner",
        process_entrypoint_runner=lambda **kwargs: calls.append(kwargs) or "done",
    )

    assert result == "done"
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
