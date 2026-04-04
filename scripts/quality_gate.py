from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def run_step(command: list[str], *, cwd: Path | None = None) -> None:
    location = cwd or REPO_ROOT
    printable = " ".join(command)
    print(f"[quality-gate] Running: {printable} (cwd={location})")
    subprocess.run(command, cwd=location, check=True)


def require_tool(tool_name: str) -> None:
    if shutil.which(tool_name):
        return
    raise SystemExit(
        f"Required tool '{tool_name}' was not found in PATH. "
        f"Install it or skip the profile that depends on it."
    )


def run_python_profile() -> None:
    run_step(
        [
            PYTHON,
            "-m",
            "ruff",
            "check",
            "scripts",
            "tests/test_chunking.py",
            "tests/test_write_json_optimization.py",
        ]
    )
    run_step([PYTHON, "-c", "import lightrag; print(lightrag.__version__)"])
    run_step(
        [
            PYTHON,
            "-m",
            "pytest",
            "tests/test_chunking.py",
            "tests/test_write_json_optimization.py",
            "-m",
            "not integration",
        ]
    )


def run_frontend_profile() -> None:
    require_tool("bun")
    webui_dir = REPO_ROOT / "lightrag_webui"
    run_step(["bun", "install", "--frozen-lockfile"], cwd=webui_dir)
    run_step(["bun", "run", "build"], cwd=webui_dir)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run LightRAG quality gates for local development and CI."
    )
    parser.add_argument(
        "--profile",
        choices=("python", "frontend", "phase-a"),
        default="phase-a",
        help="Validation profile to execute.",
    )
    args = parser.parse_args()

    if args.profile in {"python", "phase-a"}:
        run_python_profile()

    if args.profile in {"frontend", "phase-a"}:
        run_frontend_profile()

    print(f"[quality-gate] Profile '{args.profile}' completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
