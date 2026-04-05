from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

import pytest

from lightrag.api.rerank_model_factory import build_rerank_model_func


def _args(**overrides):
    defaults = {
        "rerank_binding": "null",
        "rerank_model": None,
        "rerank_binding_host": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_rerank_model_func_returns_none_when_disabled():
    assert build_rerank_model_func(_args()) is None


def test_build_rerank_model_func_fills_defaults_and_forwards_calls(monkeypatch):
    calls = []
    rerank_module = ModuleType("lightrag.rerank")

    async def fake_cohere_rerank(
        query, documents, top_n=None, extra_body=None, model="rerank-v3.5", base_url="https://cohere.example"
    ):
        calls.append((query, documents, top_n, extra_body))
        return [{"index": 0, "relevance_score": 1.0}]

    rerank_module.cohere_rerank = fake_cohere_rerank
    rerank_module.jina_rerank = fake_cohere_rerank
    rerank_module.ali_rerank = fake_cohere_rerank
    rerank_module.local_modelscope_rerank = fake_cohere_rerank
    monkeypatch.setitem(sys.modules, "lightrag.rerank", rerank_module)

    args = _args(rerank_binding="cohere")
    rerank_model_func = build_rerank_model_func(args)
    result = asyncio.run(
        rerank_model_func("q", ["a", "b"], top_n=2, extra_body={"x": 1})
    )

    assert args.rerank_model == "rerank-v3.5"
    assert args.rerank_binding_host == "https://cohere.example"
    assert result == [{"index": 0, "relevance_score": 1.0}]
    assert calls == [("q", ["a", "b"], 2, {"x": 1})]


def test_build_rerank_model_func_raises_for_unsupported_binding(monkeypatch):
    rerank_module = ModuleType("lightrag.rerank")

    async def fake_rerank(*args, **kwargs):
        return []

    rerank_module.cohere_rerank = fake_rerank
    rerank_module.jina_rerank = fake_rerank
    rerank_module.ali_rerank = fake_rerank
    rerank_module.local_modelscope_rerank = fake_rerank
    monkeypatch.setitem(sys.modules, "lightrag.rerank", rerank_module)

    with pytest.raises(ValueError, match="Unsupported rerank binding: unsupported"):
        build_rerank_model_func(_args(rerank_binding="unsupported"))
