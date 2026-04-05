from __future__ import annotations

import configparser

from dotenv import load_dotenv


def bootstrap_runtime_environment(
    dotenv_path: str = ".env",
    override: bool = False,
    config_path: str = "config.ini",
    dotenv_loader=load_dotenv,
    config_parser_factory=configparser.ConfigParser,
):
    """Load the entrypoint dotenv file and bootstrap the config parser."""
    dotenv_loader(dotenv_path=dotenv_path, override=override)
    config = config_parser_factory()
    config.read(config_path)
    return config
