from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from lightrag.api import frontend_build_checker


def _scratch_repo() -> Path:
    scratch = Path.cwd() / ".tmp" / "codex-frontend-checker" / uuid.uuid4().hex
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _silence_ascii(monkeypatch) -> None:
    monkeypatch.setattr(frontend_build_checker.ASCIIColors, "yellow", lambda *_: None)
    monkeypatch.setattr(frontend_build_checker.ASCIIColors, "cyan", lambda *_: None)


def test_check_frontend_build_returns_missing_when_index_is_absent(monkeypatch):
    scratch = _scratch_repo()
    try:
        _silence_ascii(monkeypatch)
        api_dir = scratch / "repo" / "lightrag" / "api"
        api_dir.mkdir(parents=True, exist_ok=True)

        assets_exist, is_outdated = frontend_build_checker.check_frontend_build(
            base_api_dir=api_dir
        )

        assert (assets_exist, is_outdated) == (False, False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_check_frontend_build_returns_up_to_date_when_build_is_current(monkeypatch):
    scratch = _scratch_repo()
    try:
        _silence_ascii(monkeypatch)
        api_dir = scratch / "repo" / "lightrag" / "api"
        build_file = api_dir / "webui" / "index.html"
        source_file = scratch / "repo" / "lightrag_webui" / "src" / "App.tsx"
        _write_file(build_file, "<html>built</html>")
        _write_file(source_file, "export const app = true;")

        source_time = 1_700_000_000
        build_time = source_time + 10
        source_file.touch()
        build_file.touch()
        source_file.stat()
        build_file.stat()
        import os

        os.utime(source_file, (source_time, source_time))
        os.utime(build_file, (build_time, build_time))

        assets_exist, is_outdated = frontend_build_checker.check_frontend_build(
            base_api_dir=api_dir
        )

        assert (assets_exist, is_outdated) == (True, False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_check_frontend_build_detects_when_source_is_newer(monkeypatch):
    scratch = _scratch_repo()
    try:
        _silence_ascii(monkeypatch)
        api_dir = scratch / "repo" / "lightrag" / "api"
        build_file = api_dir / "webui" / "index.html"
        source_file = scratch / "repo" / "lightrag_webui" / "src" / "App.tsx"
        _write_file(build_file, "<html>built</html>")
        _write_file(source_file, "export const app = true;")

        build_time = 1_700_000_000
        source_time = build_time + 20
        import os

        os.utime(build_file, (build_time, build_time))
        os.utime(source_file, (source_time, source_time))

        assets_exist, is_outdated = frontend_build_checker.check_frontend_build(
            base_api_dir=api_dir
        )

        assert (assets_exist, is_outdated) == (True, True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
