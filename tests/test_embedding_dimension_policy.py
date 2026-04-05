from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import embedding_dimension_policy


class _EmbeddingFuncStub:
    def __init__(self, func, embedding_dim=1024):
        self.func = func
        self.embedding_dim = embedding_dim
        self.send_dimensions = None


def _args(**overrides):
    defaults = {
        "embedding_binding": "openai",
        "embedding_send_dim": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


async def _with_embedding_dim(texts, embedding_dim=None):
    return texts, embedding_dim


async def _without_embedding_dim(texts):
    return texts


def test_apply_embedding_dimension_policy_forces_supported_binding(monkeypatch):
    messages = []
    monkeypatch.setattr(
        embedding_dimension_policy.logger,
        "info",
        lambda message: messages.append(message),
    )
    embedding_func = _EmbeddingFuncStub(_with_embedding_dim)

    embedding_dimension_policy.apply_embedding_dimension_policy(
        embedding_func, _args(embedding_binding="jina", embedding_send_dim=False)
    )

    assert embedding_func.send_dimensions is True
    assert any("forced by Jina API" in message for message in messages)


def test_apply_embedding_dimension_policy_respects_env_toggle_for_other_bindings(
    monkeypatch,
):
    messages = []
    monkeypatch.setattr(
        embedding_dimension_policy.logger,
        "info",
        lambda message: messages.append(message),
    )
    embedding_func = _EmbeddingFuncStub(_with_embedding_dim)

    embedding_dimension_policy.apply_embedding_dimension_policy(
        embedding_func, _args(embedding_binding="openai", embedding_send_dim=False)
    )

    assert embedding_func.send_dimensions is False
    assert any("by env var" in message for message in messages)


def test_apply_embedding_dimension_policy_disables_when_signature_lacks_param(
    monkeypatch,
):
    messages = []
    monkeypatch.setattr(
        embedding_dimension_policy.logger,
        "info",
        lambda message: messages.append(message),
    )
    embedding_func = _EmbeddingFuncStub(_without_embedding_dim)

    embedding_dimension_policy.apply_embedding_dimension_policy(
        embedding_func, _args(embedding_binding="openai", embedding_send_dim=True)
    )

    assert embedding_func.send_dimensions is False
    assert any("by not hasparam" in message for message in messages)
