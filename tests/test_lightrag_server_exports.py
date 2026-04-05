from __future__ import annotations

from lightrag.api import entrypoint_bootstrap_state, entrypoint_exports, lightrag_server


def test_lightrag_server_reexports_bootstrap_state_and_entrypoint_exports():
    assert lightrag_server.pm is entrypoint_bootstrap_state.pm
    assert lightrag_server.config is entrypoint_bootstrap_state.config
    assert lightrag_server.create_app is entrypoint_exports.create_app
    assert lightrag_server.get_application is entrypoint_exports.get_application
    assert lightrag_server.configure_logging is entrypoint_exports.configure_logging
    assert (
        lightrag_server.check_and_install_dependencies
        is entrypoint_exports.check_and_install_dependencies
    )
    assert lightrag_server.main is entrypoint_exports.main


def test_lightrag_server_all_declares_the_compatibility_surface():
    assert lightrag_server.__all__ == [
        "pm",
        "config",
        "create_app",
        "get_application",
        "configure_logging",
        "check_and_install_dependencies",
        "main",
    ]
