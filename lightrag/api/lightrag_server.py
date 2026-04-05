"""
LightRAG FastAPI Server
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
import os
import logging
import logging.config
import sys
import uvicorn
from pathlib import Path
import configparser
from dotenv import load_dotenv
from lightrag._pipmaster import get_pipmaster
from lightrag.api.app_cors import configure_cors
from lightrag.api.app_factory_config import build_app_kwargs
from lightrag.api.app_lifespan import create_app_lifespan
from lightrag.api.app_runtime_args import normalize_runtime_args
from lightrag.api.app_startup_state import build_app_startup_state
from lightrag.api.embedding_dimension_policy import apply_embedding_dimension_policy
from lightrag.api.embedding_model_factory import build_embedding_func
from lightrag.api.llm_config_cache import LLMConfigCache
from lightrag.api.llm_model_factory import build_llm_model_func
from lightrag.api.llm_model_kwargs import build_llm_model_kwargs
from lightrag.api.ollama_server_info import build_ollama_server_infos
from lightrag.api.query_validation_handlers import (
    create_query_validation_exception_handler,
)
from lightrag.api.rerank_model_factory import build_rerank_model_func
from lightrag.api.runtime_model_timeouts import build_runtime_model_timeouts
from lightrag.api.utils_api import display_splash_screen, check_env_file
from .config import (
    global_args,
    update_uvicorn_mode_config,
)
from lightrag.utils import get_env_value
from lightrag import LightRAG
from lightrag.api import __api_version__
from lightrag.api.app_route_context import build_route_registry_context
from lightrag.api.route_registry import register_app_routes
from lightrag.constants import (
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILENAME,
)
from lightrag.utils import logger, set_verbose_debug

pm = get_pipmaster()

# use the .env that is inside the current folder
# allows to use different .env file for each lightrag instance
# the OS environment variables take precedence over the .env file
load_dotenv(dotenv_path=".env", override=False)


# Initialize config parser
config = configparser.ConfigParser()
config.read("config.ini")
def create_app(args):
    startup_state = build_app_startup_state(args, api_version=__api_version__)

    # Setup logging
    logger.setLevel(args.log_level)
    set_verbose_debug(args.verbose)

    # Create configuration cache (this will output configuration logs)
    config_cache = LLMConfigCache(args)

    normalize_runtime_args(args)

    app_kwargs = build_app_kwargs(
        api_key=startup_state.api_key, api_version=__api_version__
    )

    # Create working directory if it doesn't exist
    Path(args.working_dir).mkdir(parents=True, exist_ok=True)

    timeouts = build_runtime_model_timeouts()
    llm_timeout = timeouts.llm_timeout
    embedding_timeout = timeouts.embedding_timeout

    # Create the EmbeddingFunc instance (now returns complete EmbeddingFunc with max_token_size)
    embedding_func = build_embedding_func(
        config_cache=config_cache,
        binding=args.embedding_binding,
        model=args.embedding_model,
        host=args.embedding_binding_host,
        api_key=args.embedding_binding_api_key,
        args=args,
    )

    apply_embedding_dimension_policy(embedding_func, args)

    rerank_model_func = build_rerank_model_func(args)

    ollama_server_infos = build_ollama_server_infos(args)

    # Initialize RAG with unified configuration
    try:
        rag = LightRAG(
            working_dir=args.working_dir,
            workspace=args.workspace,
            llm_model_func=build_llm_model_func(
                args.llm_binding,
                config_cache=config_cache,
                args=args,
                llm_timeout=llm_timeout,
            ),
            llm_model_name=args.llm_model,
            llm_model_max_async=args.max_async,
            summary_max_tokens=args.summary_max_tokens,
            summary_context_size=args.summary_context_size,
            chunk_token_size=int(args.chunk_size),
            chunk_overlap_token_size=int(args.chunk_overlap_size),
            # chunking_func=lambda tk, content, sc, sc_only, overlap, size:
            #     semantic_chunking_by_token_size(tk, content, overlap, size),
            llm_model_kwargs=build_llm_model_kwargs(
                args.llm_binding, args, llm_timeout
            ),
            embedding_func=embedding_func,
            default_llm_timeout=llm_timeout,
            default_embedding_timeout=embedding_timeout,
            kv_storage=args.kv_storage,
            graph_storage=args.graph_storage,
            vector_storage=args.vector_storage,
            doc_status_storage=args.doc_status_storage,
            vector_db_storage_cls_kwargs={
                "cosine_better_than_threshold": args.cosine_threshold
            },
            enable_llm_cache_for_entity_extract=args.enable_llm_cache_for_extract,
            enable_llm_cache=args.enable_llm_cache,
            rerank_model_func=rerank_model_func,
            max_parallel_insert=args.max_parallel_insert,
            max_graph_nodes=args.max_graph_nodes,
            addon_params={
                "language": args.summary_language,
                "entity_types": args.entity_types,
            },
            ollama_server_infos=ollama_server_infos,
        )
    except Exception as e:
        logger.error(f"Failed to initialize LightRAG: {e}")
        raise

    app = FastAPI(lifespan=create_app_lifespan(rag), **app_kwargs)

    app.exception_handler(RequestValidationError)(
        create_query_validation_exception_handler()
    )

    configure_cors(app, global_args.cors_origins)

    register_app_routes(
        app,
        build_route_registry_context(
            rag=rag,
            startup_state=startup_state,
            args=args,
            rerank_enabled=rerank_model_func is not None,
        ),
    )

    return app


def get_application(args=None):
    """Factory function for creating the FastAPI application"""
    if args is None:
        args = global_args
    return create_app(args)


def configure_logging():
    """Configure logging for uvicorn startup"""

    # Reset any existing handlers to ensure clean configuration
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "lightrag"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []

    # Get log directory path from environment variable
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, DEFAULT_LOG_FILENAME))

    print(f"\nLightRAG log file: {log_file_path}\n")
    os.makedirs(os.path.dirname(log_dir), exist_ok=True)

    # Get log file max size and backup count from environment variables
    log_max_bytes = get_env_value("LOG_MAX_BYTES", DEFAULT_LOG_MAX_BYTES, int)
    log_backup_count = get_env_value("LOG_BACKUP_COUNT", DEFAULT_LOG_BACKUP_COUNT, int)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname)s: %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "formatter": "detailed",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                # Configure all uvicorn related loggers
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                    "filters": ["path_filter"],
                },
                "uvicorn.error": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                    "filters": ["path_filter"],
                },
            },
            "filters": {
                "path_filter": {
                    "()": "lightrag.utils.LightragPathFilter",
                },
            },
        }
    )


def check_and_install_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        "uvicorn",
        "tiktoken",
        "fastapi",
        # Add other required packages here
    ]

    for package in required_packages:
        if not pm.is_installed(package):
            print(f"Installing {package}...")
            pm.install(package)
            print(f"{package} installed successfully")


def main():
    # Explicitly initialize configuration for clarity
    # (The proxy will auto-initialize anyway, but this makes intent clear)
    from .config import initialize_config

    initialize_config()

    # Check if running under Gunicorn
    if "GUNICORN_CMD_ARGS" in os.environ:
        # If started with Gunicorn, return directly as Gunicorn will call get_application
        print("Running under Gunicorn - worker management handled by Gunicorn")
        return

    # Check .env file
    if not check_env_file():
        sys.exit(1)

    # Check and install dependencies
    check_and_install_dependencies()

    from multiprocessing import freeze_support

    freeze_support()

    # Configure logging before parsing args
    configure_logging()
    update_uvicorn_mode_config()
    display_splash_screen(global_args)

    # Note: Signal handlers are NOT registered here because:
    # - Uvicorn has built-in signal handling that properly calls lifespan shutdown
    # - Custom signal handlers can interfere with uvicorn's graceful shutdown
    # - Cleanup is handled by the lifespan context manager's finally block

    # Create application instance directly instead of using factory function
    app = create_app(global_args)

    # Start Uvicorn in single process mode
    uvicorn_config = {
        "app": app,  # Pass application instance directly instead of string path
        "host": global_args.host,
        "port": global_args.port,
        "log_config": None,  # Disable default config
    }

    if global_args.ssl:
        uvicorn_config.update(
            {
                "ssl_certfile": global_args.ssl_certfile,
                "ssl_keyfile": global_args.ssl_keyfile,
            }
        )

    print(
        f"Starting Uvicorn server in single-process mode on {global_args.host}:{global_args.port}"
    )
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()
