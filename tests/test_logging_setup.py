from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import logging_setup


class FakeLogger:
    def __init__(self):
        self.handlers = ["existing-handler"]
        self.filters = ["existing-filter"]


def test_configure_server_logging_resets_handlers_and_applies_dict_config():
    loggers = {name: FakeLogger() for name in logging_setup._SERVER_LOGGER_NAMES}
    env_calls = []
    dict_configs = []
    messages = []
    makedirs_calls = []

    fake_logging_module = SimpleNamespace(
        getLogger=lambda name: loggers[name],
    )
    fake_os_module = SimpleNamespace(
        getenv=lambda key, default=None: "D:\\logs" if key == "LOG_DIR" else default,
        getcwd=lambda: "D:\\cwd",
        makedirs=lambda path, exist_ok: makedirs_calls.append((path, exist_ok)),
        path=SimpleNamespace(
            join=lambda left, right: f"{left}\\{right}",
            abspath=lambda path: f"ABS:{path}",
            dirname=lambda path: f"DIR:{path}",
        ),
    )

    def fake_get_env_value(name, default, value_type):
        env_calls.append((name, default, value_type))
        if name == "LOG_MAX_BYTES":
            return 2048
        if name == "LOG_BACKUP_COUNT":
            return 7
        raise AssertionError(name)

    log_file_path = logging_setup.configure_server_logging(
        default_log_filename="server.log",
        default_log_max_bytes=100,
        default_log_backup_count=2,
        get_env_value_func=fake_get_env_value,
        logging_module=fake_logging_module,
        dict_config_func=lambda config: dict_configs.append(config),
        os_module=fake_os_module,
        printer=lambda message: messages.append(message),
    )

    assert log_file_path == "ABS:D:\\logs\\server.log"
    assert all(logger.handlers == [] for logger in loggers.values())
    assert all(logger.filters == [] for logger in loggers.values())
    assert env_calls == [
        ("LOG_MAX_BYTES", 100, int),
        ("LOG_BACKUP_COUNT", 2, int),
    ]
    assert makedirs_calls == [("DIR:D:\\logs", True)]
    assert messages == ["\nLightRAG log file: ABS:D:\\logs\\server.log\n"]
    assert dict_configs == [
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(levelname)s: %(message)s"},
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
                    "filename": "ABS:D:\\logs\\server.log",
                    "maxBytes": 2048,
                    "backupCount": 7,
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
                }
            },
        }
    ]


def test_configure_server_logging_falls_back_to_cwd_for_log_dir():
    dict_configs = []

    fake_os_module = SimpleNamespace(
        getenv=lambda key, default=None: default,
        getcwd=lambda: "D:\\cwd",
        makedirs=lambda path, exist_ok: None,
        path=SimpleNamespace(
            join=lambda left, right: f"{left}\\{right}",
            abspath=lambda path: path,
            dirname=lambda path: "parent-dir",
        ),
    )

    log_file_path = logging_setup.configure_server_logging(
        default_log_filename="server.log",
        default_log_max_bytes=100,
        default_log_backup_count=2,
        get_env_value_func=lambda name, default, value_type: default,
        logging_module=SimpleNamespace(
            getLogger=lambda name: SimpleNamespace(handlers=[], filters=[]),
        ),
        dict_config_func=lambda config: dict_configs.append(config),
        os_module=fake_os_module,
        printer=lambda message: None,
    )

    assert log_file_path == "D:\\cwd\\server.log"
    assert dict_configs[0]["handlers"]["file"]["filename"] == "D:\\cwd\\server.log"
