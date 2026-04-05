from __future__ import annotations

from types import SimpleNamespace

from lightrag.api import rag_runtime_config


def _args(**overrides):
    defaults = {
        "working_dir": "workdir",
        "workspace": "workspace-a",
        "llm_binding": "openai",
        "llm_model": "demo-llm",
        "max_async": 4,
        "summary_max_tokens": 256,
        "summary_context_size": 2048,
        "chunk_size": "1200",
        "chunk_overlap_size": "100",
        "kv_storage": "PGKVStorage",
        "graph_storage": "Neo4JStorage",
        "vector_storage": "ChromaVectorDBStorage",
        "doc_status_storage": "PGDocStatusStorage",
        "cosine_threshold": 0.2,
        "enable_llm_cache_for_extract": True,
        "enable_llm_cache": False,
        "max_parallel_insert": 3,
        "max_graph_nodes": 99,
        "summary_language": "English",
        "entity_types": ["company", "person"],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_rag_kwargs_maps_runtime_state_and_builder_outputs(monkeypatch):
    llm_model_func = object()
    llm_model_kwargs = {"timeout": 30}
    llm_func_calls = []
    llm_kwargs_calls = []
    config_cache = object()
    embedding_func = object()
    rerank_model_func = object()
    ollama_server_infos = object()

    monkeypatch.setattr(
        rag_runtime_config,
        "build_llm_model_func",
        lambda binding, config_cache, args, llm_timeout: llm_func_calls.append(
            (binding, config_cache, args, llm_timeout)
        )
        or llm_model_func,
    )
    monkeypatch.setattr(
        rag_runtime_config,
        "build_llm_model_kwargs",
        lambda binding, args, llm_timeout: llm_kwargs_calls.append(
            (binding, args, llm_timeout)
        )
        or llm_model_kwargs,
    )

    args = _args()
    kwargs = rag_runtime_config.build_rag_kwargs(
        args=args,
        config_cache=config_cache,
        llm_timeout=30,
        embedding_timeout=12,
        embedding_func=embedding_func,
        rerank_model_func=rerank_model_func,
        ollama_server_infos=ollama_server_infos,
    )

    assert kwargs["working_dir"] == "workdir"
    assert kwargs["workspace"] == "workspace-a"
    assert kwargs["llm_model_func"] is llm_model_func
    assert kwargs["llm_model_name"] == "demo-llm"
    assert kwargs["llm_model_max_async"] == 4
    assert kwargs["summary_max_tokens"] == 256
    assert kwargs["summary_context_size"] == 2048
    assert kwargs["chunk_token_size"] == 1200
    assert kwargs["chunk_overlap_token_size"] == 100
    assert kwargs["llm_model_kwargs"] == llm_model_kwargs
    assert kwargs["embedding_func"] is embedding_func
    assert kwargs["default_llm_timeout"] == 30
    assert kwargs["default_embedding_timeout"] == 12
    assert kwargs["kv_storage"] == "PGKVStorage"
    assert kwargs["graph_storage"] == "Neo4JStorage"
    assert kwargs["vector_storage"] == "ChromaVectorDBStorage"
    assert kwargs["doc_status_storage"] == "PGDocStatusStorage"
    assert kwargs["vector_db_storage_cls_kwargs"] == {
        "cosine_better_than_threshold": 0.2
    }
    assert kwargs["enable_llm_cache_for_entity_extract"] is True
    assert kwargs["enable_llm_cache"] is False
    assert kwargs["rerank_model_func"] is rerank_model_func
    assert kwargs["max_parallel_insert"] == 3
    assert kwargs["max_graph_nodes"] == 99
    assert kwargs["addon_params"] == {
        "language": "English",
        "entity_types": ["company", "person"],
    }
    assert kwargs["ollama_server_infos"] is ollama_server_infos
    assert llm_func_calls == [("openai", config_cache, args, 30)]
    assert llm_kwargs_calls == [("openai", args, 30)]


def test_build_rag_kwargs_preserves_none_rerank_model_func(monkeypatch):
    monkeypatch.setattr(
        rag_runtime_config,
        "build_llm_model_func",
        lambda binding, config_cache, args, llm_timeout: "llm-func",
    )
    monkeypatch.setattr(
        rag_runtime_config,
        "build_llm_model_kwargs",
        lambda binding, args, llm_timeout: {},
    )

    kwargs = rag_runtime_config.build_rag_kwargs(
        args=_args(),
        config_cache=object(),
        llm_timeout=30,
        embedding_timeout=12,
        embedding_func="embedding",
        rerank_model_func=None,
        ollama_server_infos="ollama",
    )

    assert kwargs["rerank_model_func"] is None
    assert kwargs["ollama_server_infos"] == "ollama"
