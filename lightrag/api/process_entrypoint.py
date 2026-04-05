from __future__ import annotations

import os

from lightrag.api.server_startup import run_server_startup


def run_process_entrypoint(
    global_args,
    app_builder,
    dependency_checker,
    logging_configurer,
    uvicorn_mode_updater,
    env_checker,
    splash_displayer,
    initialize_config_func,
    startup_runner=run_server_startup,
    environ=None,
    printer=print,
):
    """Initialize config, choose the process mode, then delegate startup."""
    initialize_config_func()

    if environ is None:
        environ = os.environ

    if "GUNICORN_CMD_ARGS" in environ:
        printer("Running under Gunicorn - worker management handled by Gunicorn")
        return None

    return startup_runner(
        args=global_args,
        app_builder=app_builder,
        dependency_checker=dependency_checker,
        logging_configurer=logging_configurer,
        uvicorn_mode_updater=uvicorn_mode_updater,
        env_checker=env_checker,
        splash_displayer=splash_displayer,
    )
