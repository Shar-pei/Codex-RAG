from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lightrag._pipmaster import PipMasterLike, get_pipmaster
from lightrag.api.runtime_bootstrap import bootstrap_runtime_environment


@dataclass(frozen=True)
class EntrypointBootstrapState:
    package_manager: PipMasterLike
    config: Any


def build_entrypoint_bootstrap_state(
    pipmaster_getter=get_pipmaster,
    runtime_bootstrapper=bootstrap_runtime_environment,
) -> EntrypointBootstrapState:
    """Build the import-time bootstrap globals used by the API entrypoint."""
    return EntrypointBootstrapState(
        package_manager=pipmaster_getter(),
        config=runtime_bootstrapper(),
    )


BOOTSTRAP_STATE = build_entrypoint_bootstrap_state()
pm = BOOTSTRAP_STATE.package_manager
config = BOOTSTRAP_STATE.config
