from __future__ import annotations

import asyncio
from types import SimpleNamespace

from lightrag.api import app_lifespan


def _rag_stub():
    calls = []

    class RagStub:
        async def initialize_storages(self):
            calls.append("initialize")

        async def check_and_migrate_data(self):
            calls.append("migrate")

        async def finalize_storages(self):
            calls.append("finalize")

    return RagStub(), calls


def test_create_app_lifespan_runs_startup_and_uvicorn_cleanup(monkeypatch):
    rag, calls = _rag_stub()
    cleanup_calls = []
    monkeypatch.delenv("LIGHTRAG_GUNICORN_MODE", raising=False)
    monkeypatch.setattr(app_lifespan.ASCIIColors, "green", lambda *_: None)
    monkeypatch.setattr(app_lifespan, "finalize_share_data", lambda: cleanup_calls.append("cleanup"))

    async def run():
        app = SimpleNamespace(state=SimpleNamespace())
        async with app_lifespan.create_app_lifespan(rag)(app):
            assert isinstance(app.state.background_tasks, set)
            calls.append("inside")

    asyncio.run(run())

    assert calls == ["initialize", "migrate", "inside", "finalize"]
    assert cleanup_calls == ["cleanup"]


def test_create_app_lifespan_skips_shared_cleanup_in_gunicorn_mode(monkeypatch):
    rag, calls = _rag_stub()
    cleanup_calls = []
    monkeypatch.setenv("LIGHTRAG_GUNICORN_MODE", "1")
    monkeypatch.setattr(app_lifespan.ASCIIColors, "green", lambda *_: None)
    monkeypatch.setattr(app_lifespan, "finalize_share_data", lambda: cleanup_calls.append("cleanup"))

    async def run():
        app = SimpleNamespace(state=SimpleNamespace())
        async with app_lifespan.create_app_lifespan(rag)(app):
            calls.append("inside")

    asyncio.run(run())

    assert calls == ["initialize", "migrate", "inside", "finalize"]
    assert cleanup_calls == []
