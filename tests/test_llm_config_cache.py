from types import SimpleNamespace

from lightrag.api.llm_config_cache import LLMConfigCache
from lightrag.llm import binding_options


def _args(llm_binding="openai", embedding_binding="openai"):
    return SimpleNamespace(
        llm_binding=llm_binding,
        embedding_binding=embedding_binding,
    )


def test_llm_config_cache_loads_openai_options(monkeypatch):
    monkeypatch.setattr(
        binding_options.OpenAILLMOptions,
        "options_dict",
        classmethod(lambda cls, args: {"provider": args.llm_binding}),
    )

    cache = LLMConfigCache(_args(llm_binding="openai", embedding_binding="openai"))

    assert cache.openai_llm_options == {"provider": "openai"}
    assert cache.gemini_llm_options is None
    assert cache.ollama_llm_options is None


def test_llm_config_cache_loads_gemini_llm_and_embedding_options(monkeypatch):
    monkeypatch.setattr(
        binding_options.GeminiLLMOptions,
        "options_dict",
        classmethod(lambda cls, args: {"llm": args.llm_binding}),
    )
    monkeypatch.setattr(
        binding_options.GeminiEmbeddingOptions,
        "options_dict",
        classmethod(lambda cls, args: {"embedding": args.embedding_binding}),
    )

    cache = LLMConfigCache(_args(llm_binding="gemini", embedding_binding="gemini"))

    assert cache.gemini_llm_options == {"llm": "gemini"}
    assert cache.gemini_embedding_options == {"embedding": "gemini"}
    assert cache.openai_llm_options is None


def test_llm_config_cache_loads_ollama_llm_and_embedding_options(monkeypatch):
    monkeypatch.setattr(
        binding_options.OllamaLLMOptions,
        "options_dict",
        classmethod(lambda cls, args: {"llm": args.llm_binding}),
    )
    monkeypatch.setattr(
        binding_options.OllamaEmbeddingOptions,
        "options_dict",
        classmethod(lambda cls, args: {"embedding": args.embedding_binding}),
    )

    cache = LLMConfigCache(_args(llm_binding="ollama", embedding_binding="ollama"))

    assert cache.ollama_llm_options == {"llm": "ollama"}
    assert cache.ollama_embedding_options == {"embedding": "ollama"}
    assert cache.openai_llm_options is None
