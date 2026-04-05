from __future__ import annotations

import importlib

from lightrag.api import entrypoint_bootstrap_state
from lightrag.api import runtime_bootstrap
from lightrag import _pipmaster


def test_build_entrypoint_bootstrap_state_builds_package_manager_and_config():
    calls = []

    state = entrypoint_bootstrap_state.build_entrypoint_bootstrap_state(
        pipmaster_getter=lambda: calls.append("get_pipmaster") or "pm",
        runtime_bootstrapper=lambda: calls.append("bootstrap_runtime_environment")
        or "config",
    )

    assert state == entrypoint_bootstrap_state.EntrypointBootstrapState(
        package_manager="pm",
        config="config",
    )
    assert calls == [
        "get_pipmaster",
        "bootstrap_runtime_environment",
    ]


def test_module_level_bootstrap_globals_follow_helper_state(monkeypatch):
    module = entrypoint_bootstrap_state

    with monkeypatch.context() as context:
        context.setattr(_pipmaster, "get_pipmaster", lambda: "module-pm")
        context.setattr(
            runtime_bootstrap,
            "bootstrap_runtime_environment",
            lambda: "module-config",
        )
        reloaded = importlib.reload(module)

        assert reloaded.BOOTSTRAP_STATE == (
            entrypoint_bootstrap_state.EntrypointBootstrapState(
                package_manager="module-pm",
                config="module-config",
            )
        )
        assert reloaded.pm == "module-pm"
        assert reloaded.config == "module-config"

    importlib.reload(module)
