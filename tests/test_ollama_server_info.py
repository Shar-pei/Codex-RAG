from __future__ import annotations

from types import SimpleNamespace

from lightrag.api.ollama_server_info import build_ollama_server_infos


def _args(**overrides):
    defaults = {
        "simulated_model_name": "demo-family",
        "simulated_model_tag": "v1",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_ollama_server_infos_uses_runtime_args():
    server_infos = build_ollama_server_infos(_args())

    assert server_infos.LIGHTRAG_NAME == "demo-family"
    assert server_infos.LIGHTRAG_TAG == "v1"
    assert server_infos.LIGHTRAG_MODEL == "demo-family:v1"


def test_build_ollama_server_infos_preserves_env_fallbacks(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMULATING_MODEL_NAME", "env-family")
    monkeypatch.setenv("OLLAMA_EMULATING_MODEL_TAG", "env-tag")

    server_infos = build_ollama_server_infos(
        _args(simulated_model_name=None, simulated_model_tag=None)
    )

    assert server_infos.LIGHTRAG_NAME == "env-family"
    assert server_infos.LIGHTRAG_TAG == "env-tag"
    assert server_infos.LIGHTRAG_MODEL == "env-family:env-tag"
