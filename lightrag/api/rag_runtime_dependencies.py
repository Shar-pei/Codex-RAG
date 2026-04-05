from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lightrag.api.app_runtime_args import normalize_runtime_args
from lightrag.api.embedding_dimension_policy import apply_embedding_dimension_policy
from lightrag.api.embedding_model_factory import build_embedding_func
from lightrag.api.llm_config_cache import LLMConfigCache
from lightrag.api.ollama_server_info import build_ollama_server_infos
from lightrag.api.rerank_model_factory import build_rerank_model_func
from lightrag.api.runtime_model_timeouts import build_runtime_model_timeouts


@dataclass(frozen=True)
class RagRuntimeDependencies:
    config_cache: Any
    llm_timeout: int
    embedding_timeout: int
    embedding_func: Any
    rerank_model_func: Any
    ollama_server_infos: Any


def build_rag_runtime_dependencies(args) -> RagRuntimeDependencies:
    """Assemble the runtime dependency bundle consumed by `build_rag(...)`."""
    config_cache = LLMConfigCache(args)
    normalize_runtime_args(args)

    timeouts = build_runtime_model_timeouts()
    embedding_func = build_embedding_func(
        config_cache=config_cache,
        binding=args.embedding_binding,
        model=args.embedding_model,
        host=args.embedding_binding_host,
        api_key=args.embedding_binding_api_key,
        args=args,
    )
    apply_embedding_dimension_policy(embedding_func, args)

    rerank_model_func = build_rerank_model_func(args)
    ollama_server_infos = build_ollama_server_infos(args)

    return RagRuntimeDependencies(
        config_cache=config_cache,
        llm_timeout=timeouts.llm_timeout,
        embedding_timeout=timeouts.embedding_timeout,
        embedding_func=embedding_func,
        rerank_model_func=rerank_model_func,
        ollama_server_infos=ollama_server_infos,
    )
