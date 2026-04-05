from types import SimpleNamespace

from lightrag.api import llm_model_kwargs
from lightrag.llm import binding_options


def _args():
    return SimpleNamespace(
        llm_binding_host="http://localhost:11434",
        llm_binding_api_key="secret",
    )


def test_build_llm_model_kwargs_for_ollama_compatible_binding(monkeypatch):
    monkeypatch.setattr(
        binding_options.OllamaLLMOptions,
        "options_dict",
        classmethod(lambda cls, args: {"temperature": 0.2}),
    )

    kwargs = llm_model_kwargs.build_llm_model_kwargs("ollama", _args(), 30)

    assert kwargs == {
        "host": "http://localhost:11434",
        "timeout": 30,
        "options": {"temperature": 0.2},
        "api_key": "secret",
    }


def test_build_llm_model_kwargs_returns_empty_for_other_bindings():
    assert llm_model_kwargs.build_llm_model_kwargs("openai", _args(), 30) == {}
