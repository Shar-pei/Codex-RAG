from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

from lightrag.api import llm_model_factory
from lightrag.api.llm_model_factory import build_llm_model_func
def _args():
    return SimpleNamespace(
        llm_model="demo-model",
        llm_binding_host="http://localhost",
        llm_binding_api_key="secret",
    )


def test_build_llm_model_func_openai_wrapper_merges_timeout_and_cache(monkeypatch):
    calls = []
    openai_module = ModuleType("lightrag.llm.openai")

    async def fake_openai_complete_if_cache(model, prompt, **kwargs):
        calls.append((model, prompt, kwargs))
        return "ok"

    openai_module.openai_complete_if_cache = fake_openai_complete_if_cache
    monkeypatch.setitem(sys.modules, "lightrag.llm.openai", openai_module)

    config_cache = SimpleNamespace(openai_llm_options={"temperature": 0.2})
    model_func = build_llm_model_func(
        "openai",
        config_cache=config_cache,
        args=_args(),
        llm_timeout=30,
    )

    result = asyncio.run(model_func("hello", keyword_extraction=True))

    assert result == "ok"
    assert calls == [
        (
            "demo-model",
            "hello",
            {
                "system_prompt": None,
                "history_messages": [],
                "base_url": "http://localhost",
                "api_key": "secret",
                "timeout": 30,
                "temperature": 0.2,
            },
        )
    ]


def test_build_llm_model_func_gemini_injects_generation_config(monkeypatch):
    calls = []
    gemini_module = ModuleType("lightrag.llm.gemini")

    async def fake_gemini_complete_if_cache(model, prompt, **kwargs):
        calls.append((model, prompt, kwargs))
        return "ok"

    gemini_module.gemini_complete_if_cache = fake_gemini_complete_if_cache
    monkeypatch.setitem(sys.modules, "lightrag.llm.gemini", gemini_module)

    config_cache = SimpleNamespace(gemini_llm_options={"candidate_count": 1})
    model_func = build_llm_model_func(
        "gemini",
        config_cache=config_cache,
        args=_args(),
        llm_timeout=45,
    )

    result = asyncio.run(model_func("hello"))

    assert result == "ok"
    assert calls == [
        (
            "demo-model",
            "hello",
            {
                "system_prompt": None,
                "history_messages": [],
                "api_key": "secret",
                "base_url": "http://localhost",
                "keyword_extraction": False,
                "timeout": 45,
                "generation_config": {"candidate_count": 1},
            },
        )
    ]


def test_build_llm_model_func_builds_bedrock_callable(monkeypatch):
    calls = []
    bedrock_module = ModuleType("lightrag.llm.bedrock")

    async def fake_bedrock_complete_if_cache(model, prompt, **kwargs):
        calls.append((model, prompt, kwargs))
        return "ok"

    bedrock_module.bedrock_complete_if_cache = fake_bedrock_complete_if_cache
    monkeypatch.setitem(sys.modules, "lightrag.llm.bedrock", bedrock_module)
    monkeypatch.setattr(
        llm_model_factory,
        "get_env_value",
        lambda name, default, value_type: 0.7,
    )

    model_func = build_llm_model_func(
        "aws_bedrock",
        config_cache=SimpleNamespace(),
        args=_args(),
        llm_timeout=30,
    )

    result = asyncio.run(model_func("hello"))

    assert result == "ok"
    assert calls == [
        (
            "demo-model",
            "hello",
            {
                "system_prompt": None,
                "history_messages": [],
                "temperature": 0.7,
            },
        )
    ]
