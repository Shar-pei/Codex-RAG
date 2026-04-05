from __future__ import annotations

import logging
import os

from lightrag.api import __api_version__, entrypoint_bootstrap_state
from lightrag.api.entrypoint_facade import (
    check_dependencies_with_bindings,
    configure_logging_with_bindings,
    create_app_with_bindings,
    run_main_with_bindings,
)
from lightrag.api.server_startup import run_server_startup
from lightrag.constants import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILENAME,
    DEFAULT_LOG_MAX_BYTES,
)
from lightrag.utils import get_env_value

from .config import global_args, update_uvicorn_mode_config


pm = entrypoint_bootstrap_state.pm


def resolve_entrypoint_runtime_helpers():
    from lightrag.api.utils_api import check_env_file, display_splash_screen

    return check_env_file, display_splash_screen


def create_app(args):
    return create_app_with_bindings(
        args=args,
        api_version=__api_version__,
        cors_origins=global_args.cors_origins,
    )


def get_application(args=None):
    """Factory function for creating the FastAPI application."""
    if args is None:
        args = global_args
    return create_app(args)


def configure_logging():
    """Configure logging for uvicorn startup."""
    configure_logging_with_bindings(
        default_log_filename=DEFAULT_LOG_FILENAME,
        default_log_max_bytes=DEFAULT_LOG_MAX_BYTES,
        default_log_backup_count=DEFAULT_LOG_BACKUP_COUNT,
        get_env_value_func=get_env_value,
        logging_module=logging,
        os_module=os,
        printer=print,
    )


def check_and_install_dependencies():
    """Check and install required dependencies."""
    check_dependencies_with_bindings(package_manager=pm)


def main():
    from .config import initialize_config

    env_checker, splash_displayer = resolve_entrypoint_runtime_helpers()

    run_main_with_bindings(
        global_args=global_args,
        app_builder=create_app,
        dependency_checker=check_and_install_dependencies,
        logging_configurer=configure_logging,
        uvicorn_mode_updater=update_uvicorn_mode_config,
        env_checker=env_checker,
        splash_displayer=splash_displayer,
        initialize_config_func=initialize_config,
        startup_runner=run_server_startup,
    )
