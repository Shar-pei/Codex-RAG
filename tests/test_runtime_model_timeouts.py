from __future__ import annotations

from lightrag.api.runtime_model_timeouts import build_runtime_model_timeouts
from lightrag.constants import DEFAULT_EMBEDDING_TIMEOUT, DEFAULT_LLM_TIMEOUT


def test_build_runtime_model_timeouts_uses_defaults(monkeypatch):
    monkeypatch.delenv("LLM_TIMEOUT", raising=False)
    monkeypatch.delenv("EMBEDDING_TIMEOUT", raising=False)

    timeouts = build_runtime_model_timeouts()

    assert timeouts.llm_timeout == DEFAULT_LLM_TIMEOUT
    assert timeouts.embedding_timeout == DEFAULT_EMBEDDING_TIMEOUT


def test_build_runtime_model_timeouts_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT", "45")
    monkeypatch.setenv("EMBEDDING_TIMEOUT", "12")

    timeouts = build_runtime_model_timeouts()

    assert timeouts.llm_timeout == 45
    assert timeouts.embedding_timeout == 12
