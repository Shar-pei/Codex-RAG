"""
LightRAG FastAPI Server
"""

from lightrag.api import entrypoint_bootstrap_state
from lightrag.api.entrypoint_exports import (
    check_and_install_dependencies,
    configure_logging,
    create_app,
    get_application,
    main,
)


pm = entrypoint_bootstrap_state.pm
config = entrypoint_bootstrap_state.config

__all__ = [
    "pm",
    "config",
    "create_app",
    "get_application",
    "configure_logging",
    "check_and_install_dependencies",
    "main",
]


if __name__ == "__main__":
    main()
