"""
LightRAG FastAPI Server
"""

import os
import logging
import configparser
from dotenv import load_dotenv
from lightrag._pipmaster import get_pipmaster
from lightrag.api.app_composition import build_app_composition
from lightrag.api.dependency_bootstrap import ensure_required_packages
from lightrag.api.logging_setup import configure_server_logging
from lightrag.api.process_entrypoint import run_process_entrypoint
from lightrag.api.server_startup import run_server_startup
from lightrag.api.utils_api import display_splash_screen, check_env_file
from .config import (
    global_args,
    update_uvicorn_mode_config,
)
from lightrag.utils import get_env_value
from lightrag.api import __api_version__
from lightrag.constants import (
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILENAME,
)


pm = get_pipmaster()

# use the .env that is inside the current folder
# allows to use different .env file for each lightrag instance
# the OS environment variables take precedence over the .env file
load_dotenv(dotenv_path=".env", override=False)


# Initialize config parser
config = configparser.ConfigParser()
config.read("config.ini")


def create_app(args):
    return build_app_composition(
        args=args,
        api_version=__api_version__,
        cors_origins=global_args.cors_origins,
    )


def get_application(args=None):
    """Factory function for creating the FastAPI application"""
    if args is None:
        args = global_args
    return create_app(args)


def configure_logging():
    """Configure logging for uvicorn startup."""
    configure_server_logging(
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
    required_packages = [
        "uvicorn",
        "tiktoken",
        "fastapi",
        # Add other required packages here
    ]
    ensure_required_packages(required_packages=required_packages, package_manager=pm)


def main():
    from .config import initialize_config

    run_process_entrypoint(
        global_args=global_args,
        app_builder=create_app,
        dependency_checker=check_and_install_dependencies,
        logging_configurer=configure_logging,
        uvicorn_mode_updater=update_uvicorn_mode_config,
        env_checker=check_env_file,
        splash_displayer=display_splash_screen,
        initialize_config_func=initialize_config,
        startup_runner=run_server_startup,
    )


if __name__ == "__main__":
    main()
