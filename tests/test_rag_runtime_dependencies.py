from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import rag_runtime_dependencies


def _args(**overrides):
    defaults = {
        "embedding_binding": "openai",
        "embedding_model": "demo-embedding",
        "embedding_binding_host": None,
        "embedding_binding_api_key": "embedding-key",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_rag_runtime_dependencies_assembles_bundle_in_order(monkeypatch):
    args = _args()
    config_cache = object()
    embedding_func = object()
    rerank_model_func = object()
    ollama_server_infos = object()
    call_order = []

    monkeypatch.setattr(
        rag_runtime_dependencies,
        "LLMConfigCache",
        lambda actual_args: call_order.append(("config_cache", actual_args))
        or config_cache,
    )

    def fake_normalize_runtime_args(actual_args):
        call_order.append(("normalize", actual_args))
        actual_args.embedding_binding_host = "https://embedding.example.com"
        return actual_args

    monkeypatch.setattr(
        rag_runtime_dependencies,
        "normalize_runtime_args",
        fake_normalize_runtime_args,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_runtime_model_timeouts",
        lambda: call_order.append(("timeouts",))
        or SimpleNamespace(llm_timeout=30, embedding_timeout=12),
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_embedding_func",
        lambda **kwargs: call_order.append(("embedding", kwargs)) or embedding_func,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "apply_embedding_dimension_policy",
        lambda actual_embedding_func, actual_args: call_order.append(
            ("dimension_policy", actual_embedding_func, actual_args)
        ),
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_rerank_model_func",
        lambda actual_args: call_order.append(("rerank", actual_args))
        or rerank_model_func,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_ollama_server_infos",
        lambda actual_args: call_order.append(("ollama", actual_args))
        or ollama_server_infos,
    )

    dependencies = rag_runtime_dependencies.build_rag_runtime_dependencies(args)

    assert dependencies == rag_runtime_dependencies.RagRuntimeDependencies(
        config_cache=config_cache,
        llm_timeout=30,
        embedding_timeout=12,
        embedding_func=embedding_func,
        rerank_model_func=rerank_model_func,
        ollama_server_infos=ollama_server_infos,
    )
    assert call_order == [
        ("config_cache", args),
        ("normalize", args),
        ("timeouts",),
        (
            "embedding",
            {
                "config_cache": config_cache,
                "binding": "openai",
                "model": "demo-embedding",
                "host": "https://embedding.example.com",
                "api_key": "embedding-key",
                "args": args,
            },
        ),
        ("dimension_policy", embedding_func, args),
        ("rerank", args),
        ("ollama", args),
    ]


def test_build_rag_runtime_dependencies_preserves_optional_none_rerank(monkeypatch):
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "LLMConfigCache",
        lambda actual_args: "config-cache",
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "normalize_runtime_args",
        lambda actual_args: actual_args,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_runtime_model_timeouts",
        lambda: SimpleNamespace(llm_timeout=30, embedding_timeout=12),
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_embedding_func",
        lambda **kwargs: "embedding-func",
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "apply_embedding_dimension_policy",
        lambda actual_embedding_func, actual_args: None,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_rerank_model_func",
        lambda actual_args: None,
    )
    monkeypatch.setattr(
        rag_runtime_dependencies,
        "build_ollama_server_infos",
        lambda actual_args: "ollama-info",
    )

    dependencies = rag_runtime_dependencies.build_rag_runtime_dependencies(_args())

    assert dependencies.rerank_model_func is None
    assert dependencies.ollama_server_infos == "ollama-info"
