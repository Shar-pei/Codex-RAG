from __future__ import annotations

from lightrag.api.app_factory_config import build_app_kwargs
from lightrag.api.app_shell_factory import build_app_shell
from lightrag.api.app_startup_state import build_app_startup_state
from lightrag.api.rag_app_runtime import build_rag_app_runtime
from lightrag.api.rag_runtime_dependencies import build_rag_runtime_dependencies
from lightrag.utils import logger, set_verbose_debug


def build_app_composition(
    args,
    api_version: str,
    cors_origins,
    startup_state_builder=build_app_startup_state,
    runtime_dependencies_builder=build_rag_runtime_dependencies,
    app_kwargs_builder=build_app_kwargs,
    app_runtime_builder=build_rag_app_runtime,
    app_shell_builder=build_app_shell,
    runtime_logger=logger,
    verbose_debug_setter=set_verbose_debug,
):
    """Compose the application from startup, runtime, and app-shell helpers."""
    startup_state = startup_state_builder(args, api_version=api_version)

    runtime_logger.setLevel(args.log_level)
    verbose_debug_setter(args.verbose)

    runtime_dependencies = runtime_dependencies_builder(args)
    app_kwargs = app_kwargs_builder(
        api_key=startup_state.api_key, api_version=api_version
    )
    app_runtime = app_runtime_builder(args, runtime_dependencies)

    return app_shell_builder(
        app_runtime=app_runtime,
        startup_state=startup_state,
        args=args,
        app_kwargs=app_kwargs,
        cors_origins=cors_origins,
    )
