"""
LightRAG FastAPI Server
"""

from lightrag.api.entrypoint_bootstrap_state import config, pm
from lightrag.api.entrypoint_exports import (
    check_and_install_dependencies,
    configure_logging,
    create_app,
    get_application,
    main,
)


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
