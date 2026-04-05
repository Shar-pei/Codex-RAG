from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from typing import Protocol


class PipMasterLike(Protocol):
    def is_installed(self, package_name: str) -> bool: ...

    def install(self, package_name: str) -> None: ...


class _PipMasterFallback:
    def is_installed(self, package_name: str) -> bool:
        return importlib.util.find_spec(package_name) is not None

    def install(self, package_name: str) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def get_pipmaster() -> PipMasterLike:
    try:
        return importlib.import_module("pipmaster")
    except ModuleNotFoundError:
        return _PipMasterFallback()


def import_or_install(module_name: str, package_name: str | None = None):
    package_name = package_name or module_name.split(".", 1)[0]
    pm = get_pipmaster()
    if not pm.is_installed(package_name):
        pm.install(package_name)
    return importlib.import_module(module_name)
