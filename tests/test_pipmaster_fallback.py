from __future__ import annotations

import sys
from types import SimpleNamespace

from lightrag._pipmaster import get_pipmaster, import_or_install


def test_get_pipmaster_prefers_installed_module(monkeypatch):
    fake_module = SimpleNamespace(
        is_installed=lambda package_name: True,
        install=lambda package_name: None,
    )

    def fake_import_module(module_name: str):
        assert module_name == "pipmaster"
        return fake_module

    monkeypatch.setattr("lightrag._pipmaster.importlib.import_module", fake_import_module)

    assert get_pipmaster() is fake_module


def test_get_pipmaster_returns_local_fallback(monkeypatch):
    def fake_import_module(module_name: str):
        raise ModuleNotFoundError(module_name)

    install_calls: list[list[str]] = []

    monkeypatch.setattr("lightrag._pipmaster.importlib.import_module", fake_import_module)
    monkeypatch.setattr(
        "lightrag._pipmaster.importlib.util.find_spec",
        lambda package_name: object() if package_name == "available-package" else None,
    )
    monkeypatch.setattr(
        "lightrag._pipmaster.subprocess.check_call",
        lambda command: install_calls.append(command),
    )

    fallback = get_pipmaster()

    assert fallback.is_installed("available-package")
    assert not fallback.is_installed("missing-package")

    fallback.install("demo-package")

    assert install_calls == [[sys.executable, "-m", "pip", "install", "demo-package"]]


def test_import_or_install_imports_requested_module(monkeypatch):
    fake_pm = SimpleNamespace(
        is_installed=lambda package_name: package_name == "demo-package",
        install=lambda package_name: None,
    )
    imported_modules: list[str] = []

    def fake_import_module(module_name: str):
        if module_name == "pipmaster":
            return fake_pm
        imported_modules.append(module_name)
        return SimpleNamespace(module_name=module_name)

    monkeypatch.setattr("lightrag._pipmaster.importlib.import_module", fake_import_module)

    module = import_or_install("demo.module", package_name="demo-package")

    assert module.module_name == "demo.module"
    assert imported_modules == ["demo.module"]
