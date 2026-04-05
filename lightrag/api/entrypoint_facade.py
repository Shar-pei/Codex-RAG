from __future__ import annotations

from lightrag.api.app_composition import build_app_composition
from lightrag.api.dependency_bootstrap import ensure_required_packages
from lightrag.api.logging_setup import configure_server_logging
from lightrag.api.process_entrypoint import run_process_entrypoint


DEFAULT_REQUIRED_PACKAGES = (
    "uvicorn",
    "tiktoken",
    "fastapi",
)


def create_app_with_bindings(
    args,
    api_version: str,
    cors_origins,
    app_composer=build_app_composition,
):
    """Create the API app using the entrypoint's bound globals."""
    return app_composer(
        args=args,
        api_version=api_version,
        cors_origins=cors_origins,
    )


def configure_logging_with_bindings(
    default_log_filename: str,
    default_log_max_bytes: int,
    default_log_backup_count: int,
    get_env_value_func,
    logging_module,
    os_module,
    printer=print,
    logging_configurer=configure_server_logging,
):
    """Apply the entrypoint's bound logging configuration helpers."""
    return logging_configurer(
        default_log_filename=default_log_filename,
        default_log_max_bytes=default_log_max_bytes,
        default_log_backup_count=default_log_backup_count,
        get_env_value_func=get_env_value_func,
        logging_module=logging_module,
        os_module=os_module,
        printer=printer,
    )


def check_dependencies_with_bindings(
    package_manager,
    required_packages=DEFAULT_REQUIRED_PACKAGES,
    dependency_bootstrapper=ensure_required_packages,
):
    """Install any missing required packages using the entrypoint bindings."""
    dependency_bootstrapper(
        required_packages=list(required_packages),
        package_manager=package_manager,
    )


def run_main_with_bindings(
    global_args,
    app_builder,
    dependency_checker,
    logging_configurer,
    uvicorn_mode_updater,
    env_checker,
    splash_displayer,
    initialize_config_func,
    startup_runner,
    process_entrypoint_runner=run_process_entrypoint,
):
    """Run the process entrypoint using the entrypoint's bound globals."""
    return process_entrypoint_runner(
        global_args=global_args,
        app_builder=app_builder,
        dependency_checker=dependency_checker,
        logging_configurer=logging_configurer,
        uvicorn_mode_updater=uvicorn_mode_updater,
        env_checker=env_checker,
        splash_displayer=splash_displayer,
        initialize_config_func=initialize_config_func,
        startup_runner=startup_runner,
    )
