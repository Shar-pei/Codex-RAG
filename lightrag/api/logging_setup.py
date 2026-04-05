from __future__ import annotations

import logging
import logging.config
import os

from lightrag.utils import get_env_value


_SERVER_LOGGER_NAMES = ("uvicorn", "uvicorn.access", "uvicorn.error", "lightrag")


def configure_server_logging(
    default_log_filename: str,
    default_log_max_bytes: int,
    default_log_backup_count: int,
    get_env_value_func=get_env_value,
    logging_module=logging,
    dict_config_func=logging.config.dictConfig,
    os_module=os,
    printer=print,
):
    """Reset logging handlers and apply the server logging dictConfig payload."""
    for logger_name in _SERVER_LOGGER_NAMES:
        logger = logging_module.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []

    log_dir = os_module.getenv("LOG_DIR", os_module.getcwd())
    log_file_path = os_module.path.abspath(
        os_module.path.join(log_dir, default_log_filename)
    )

    printer(f"\nLightRAG log file: {log_file_path}\n")
    os_module.makedirs(os_module.path.dirname(log_dir), exist_ok=True)

    log_max_bytes = get_env_value_func(
        "LOG_MAX_BYTES", default_log_max_bytes, int
    )
    log_backup_count = get_env_value_func(
        "LOG_BACKUP_COUNT", default_log_backup_count, int
    )

    dict_config_func(
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

    return log_file_path
