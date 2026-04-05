from __future__ import annotations


def ensure_required_packages(required_packages, package_manager, printer=print):
    """Install any required packages that are missing from the runtime."""
    for package in required_packages:
        if not package_manager.is_installed(package):
            printer(f"Installing {package}...")
            package_manager.install(package)
            printer(f"{package} installed successfully")
