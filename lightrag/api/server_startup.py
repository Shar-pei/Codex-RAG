from __future__ import annotations

import sys
import uvicorn


def run_server_startup(
    args,
    app_builder,
    dependency_checker,
    logging_configurer,
    uvicorn_mode_updater,
    env_checker=None,
    splash_displayer=None,
    freeze_support_func=None,
    uvicorn_runner=uvicorn.run,
    exit_func=sys.exit,
):
    """Run the single-process API startup flow before handing off to Uvicorn."""
    if env_checker is None or splash_displayer is None:
        from lightrag.api.utils_api import check_env_file, display_splash_screen

        if env_checker is None:
            env_checker = check_env_file
        if splash_displayer is None:
            splash_displayer = display_splash_screen

    if not env_checker():
        exit_func(1)
        return None

    dependency_checker()

    if freeze_support_func is None:
        from multiprocessing import freeze_support

        freeze_support_func = freeze_support

    freeze_support_func()

    logging_configurer()
    uvicorn_mode_updater()
    splash_displayer(args)

    app = app_builder(args)

    uvicorn_config = {
        "app": app,
        "host": args.host,
        "port": args.port,
        "log_config": None,
    }

    if args.ssl:
        uvicorn_config.update(
            {
                "ssl_certfile": args.ssl_certfile,
                "ssl_keyfile": args.ssl_keyfile,
            }
        )

    print(
        f"Starting Uvicorn server in single-process mode on {args.host}:{args.port}"
    )
    uvicorn_runner(**uvicorn_config)
    return app
