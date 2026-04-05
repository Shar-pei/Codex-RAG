from __future__ import annotations

from types import SimpleNamespace

import pytest

from lightrag.api import rag_runtime_factory


def _args():
    return SimpleNamespace()


def test_build_rag_forwards_kwargs_into_rag_factory(monkeypatch):
    args = _args()
    build_calls = []
    rag_calls = []

    monkeypatch.setattr(
        rag_runtime_factory,
        "build_rag_kwargs",
        lambda **kwargs: build_calls.append(kwargs)
        or {"working_dir": "workdir", "embedding_func": "embedding"},
    )

    def fake_rag_factory(**kwargs):
        rag_calls.append(kwargs)
        return "rag-instance"

    result = rag_runtime_factory.build_rag(
        args=args,
        config_cache="cache",
        llm_timeout=30,
        embedding_timeout=12,
        embedding_func="embedding",
        rerank_model_func="rerank",
        ollama_server_infos="ollama",
        rag_factory=fake_rag_factory,
    )

    assert result == "rag-instance"
    assert build_calls == [
        {
            "args": args,
            "config_cache": "cache",
            "llm_timeout": 30,
            "embedding_timeout": 12,
            "embedding_func": "embedding",
            "rerank_model_func": "rerank",
            "ollama_server_infos": "ollama",
        }
    ]
    assert rag_calls == [{"working_dir": "workdir", "embedding_func": "embedding"}]


def test_build_rag_logs_and_reraises_failures(monkeypatch):
    messages = []
    monkeypatch.setattr(
        rag_runtime_factory,
        "build_rag_kwargs",
        lambda **kwargs: {"working_dir": "workdir"},
    )
    monkeypatch.setattr(
        rag_runtime_factory.logger,
        "error",
        lambda message: messages.append(message),
    )

    def fake_rag_factory(**kwargs):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        rag_runtime_factory.build_rag(
            args=_args(),
            config_cache="cache",
            llm_timeout=30,
            embedding_timeout=12,
            embedding_func="embedding",
            rerank_model_func=None,
            ollama_server_infos="ollama",
            rag_factory=fake_rag_factory,
        )

    assert messages == ["Failed to initialize LightRAG: boom"]
