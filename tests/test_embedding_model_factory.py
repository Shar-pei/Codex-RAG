from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

from lightrag.api.embedding_model_factory import build_embedding_func
from lightrag.utils import EmbeddingFunc


def _args(**overrides):
    defaults = {
        "embedding_dim": None,
        "embedding_token_limit": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_embedding_func_inherits_provider_defaults_and_wraps_openai(monkeypatch):
    calls = []
    openai_module = ModuleType("lightrag.llm.openai")

    async def fake_openai_embed(
        texts, model=None, base_url=None, api_key=None, embedding_dim=None
    ):
        calls.append((texts, model, base_url, api_key, embedding_dim))
        return [[0.1, 0.2]]

    openai_module.openai_embed = EmbeddingFunc(
        embedding_dim=256,
        max_token_size=8192,
        func=fake_openai_embed,
    )
    monkeypatch.setitem(sys.modules, "lightrag.llm.openai", openai_module)

    embedding_func = build_embedding_func(
        config_cache=SimpleNamespace(
            ollama_embedding_options=None,
            gemini_embedding_options=None,
        ),
        binding="openai",
        model="demo-model",
        host="http://localhost",
        api_key="secret",
        args=_args(),
    )

    result = asyncio.run(embedding_func.func(["hello"], embedding_dim=128))

    assert result == [[0.1, 0.2]]
    assert embedding_func.embedding_dim == 256
    assert embedding_func.max_token_size == 8192
    assert embedding_func.send_dimensions is False
    assert calls == [
        (["hello"], "demo-model", "http://localhost", "secret", 128),
    ]


def test_build_embedding_func_uses_cached_ollama_options(monkeypatch):
    calls = []
    ollama_module = ModuleType("lightrag.llm.ollama")

    async def fake_ollama_embed(
        texts, embed_model=None, host=None, api_key=None, options=None
    ):
        calls.append((texts, embed_model, host, api_key, options))
        return [[0.3, 0.4]]

    ollama_module.ollama_embed = fake_ollama_embed
    monkeypatch.setitem(sys.modules, "lightrag.llm.ollama", ollama_module)

    embedding_func = build_embedding_func(
        config_cache=SimpleNamespace(
            ollama_embedding_options={"num_ctx": 4096},
            gemini_embedding_options=None,
        ),
        binding="ollama",
        model="demo-model",
        host="http://localhost:11434",
        api_key="secret",
        args=_args(embedding_dim=1024, embedding_token_limit=2048),
    )

    result = asyncio.run(embedding_func.func(["hello"]))

    assert result == [[0.3, 0.4]]
    assert embedding_func.embedding_dim == 1024
    assert embedding_func.max_token_size == 2048
    assert calls == [
        (
            ["hello"],
            "demo-model",
            "http://localhost:11434",
            "secret",
            {"num_ctx": 4096},
        ),
    ]


def test_build_embedding_func_uses_modelscope_initializer(monkeypatch):
    init_calls = []
    embed_calls = []
    hf_module = ModuleType("lightrag.llm.hf")

    async def fake_modelscope_embed(texts, tokenizer=None, embed_model=None):
        embed_calls.append((texts, tokenizer, embed_model))
        return [[0.5, 0.6]]

    def fake_initialize_bge_model_optimized(model_path):
        init_calls.append(model_path)
        return "tokenizer", "embed-model"

    hf_module.modelscope_embed = EmbeddingFunc(
        embedding_dim=768,
        max_token_size=4096,
        func=fake_modelscope_embed,
    )
    hf_module.initialize_bge_model_optimized = fake_initialize_bge_model_optimized
    monkeypatch.setitem(sys.modules, "lightrag.llm.hf", hf_module)
    monkeypatch.setenv("HF_EMBEDDING_MODEL_PATH", r"D:\models\demo-bge")

    embedding_func = build_embedding_func(
        config_cache=SimpleNamespace(
            ollama_embedding_options=None,
            gemini_embedding_options=None,
        ),
        binding="modelscope",
        model="ignored",
        host="ignored",
        api_key="ignored",
        args=_args(),
    )

    result = asyncio.run(embedding_func.func(["hello"]))

    assert result == [[0.5, 0.6]]
    assert embedding_func.embedding_dim == 768
    assert embedding_func.max_token_size == 4096
    assert init_calls == [r"D:\models\demo-bge"]
    assert embed_calls == [(["hello"], "tokenizer", "embed-model")]
