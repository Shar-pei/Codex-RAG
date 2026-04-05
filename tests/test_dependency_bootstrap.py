from __future__ import annotations

from lightrag.api import dependency_bootstrap


class FakePackageManager:
    def __init__(self, installed=None):
        self.installed = set(installed or [])
        self.checked = []
        self.installs = []

    def is_installed(self, package):
        self.checked.append(package)
        return package in self.installed

    def install(self, package):
        self.installs.append(package)


def test_ensure_required_packages_skips_installed_packages():
    package_manager = FakePackageManager(installed={"uvicorn", "fastapi"})
    messages = []

    dependency_bootstrap.ensure_required_packages(
        required_packages=["uvicorn", "fastapi"],
        package_manager=package_manager,
        printer=lambda message: messages.append(message),
    )

    assert package_manager.checked == ["uvicorn", "fastapi"]
    assert package_manager.installs == []
    assert messages == []


def test_ensure_required_packages_installs_missing_packages_in_order():
    package_manager = FakePackageManager(installed={"uvicorn"})
    messages = []

    dependency_bootstrap.ensure_required_packages(
        required_packages=["uvicorn", "tiktoken", "fastapi"],
        package_manager=package_manager,
        printer=lambda message: messages.append(message),
    )

    assert package_manager.checked == ["uvicorn", "tiktoken", "fastapi"]
    assert package_manager.installs == ["tiktoken", "fastapi"]
    assert messages == [
        "Installing tiktoken...",
        "tiktoken installed successfully",
        "Installing fastapi...",
        "fastapi installed successfully",
    ]
