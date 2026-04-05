from __future__ import annotations

from lightrag.api.llm_model_factory import build_llm_model_func
from lightrag.api.llm_model_kwargs import build_llm_model_kwargs


def build_rag_kwargs(
    args,
    config_cache,
    llm_timeout: int,
    embedding_timeout: int,
    embedding_func,
    rerank_model_func,
    ollama_server_infos,
) -> dict:
    """Build the LightRAG constructor kwargs from runtime state."""
    return {
        "working_dir": args.working_dir,
        "workspace": args.workspace,
        "llm_model_func": build_llm_model_func(
            args.llm_binding,
            config_cache=config_cache,
            args=args,
            llm_timeout=llm_timeout,
        ),
        "llm_model_name": args.llm_model,
        "llm_model_max_async": args.max_async,
        "summary_max_tokens": args.summary_max_tokens,
        "summary_context_size": args.summary_context_size,
        "chunk_token_size": int(args.chunk_size),
        "chunk_overlap_token_size": int(args.chunk_overlap_size),
        "llm_model_kwargs": build_llm_model_kwargs(
            args.llm_binding, args, llm_timeout
        ),
        "embedding_func": embedding_func,
        "default_llm_timeout": llm_timeout,
        "default_embedding_timeout": embedding_timeout,
        "kv_storage": args.kv_storage,
        "graph_storage": args.graph_storage,
        "vector_storage": args.vector_storage,
        "doc_status_storage": args.doc_status_storage,
        "vector_db_storage_cls_kwargs": {
            "cosine_better_than_threshold": args.cosine_threshold
        },
        "enable_llm_cache_for_entity_extract": args.enable_llm_cache_for_extract,
        "enable_llm_cache": args.enable_llm_cache,
        "rerank_model_func": rerank_model_func,
        "max_parallel_insert": args.max_parallel_insert,
        "max_graph_nodes": args.max_graph_nodes,
        "addon_params": {
            "language": args.summary_language,
            "entity_types": args.entity_types,
        },
        "ollama_server_infos": ollama_server_infos,
    }
