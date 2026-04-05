from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lightrag.api.rag_runtime_factory import build_rag


@dataclass(frozen=True)
class RagAppRuntime:
    rag: Any
    rerank_enabled: bool


def build_rag_app_runtime(
    args,
    runtime_dependencies,
    rag_builder=build_rag,
    path_class=Path,
) -> RagAppRuntime:
    """Prepare the working directory and bootstrap the runtime RAG instance."""
    path_class(args.working_dir).mkdir(parents=True, exist_ok=True)

    rag = rag_builder(
        args=args,
        config_cache=runtime_dependencies.config_cache,
        llm_timeout=runtime_dependencies.llm_timeout,
        embedding_timeout=runtime_dependencies.embedding_timeout,
        embedding_func=runtime_dependencies.embedding_func,
        rerank_model_func=runtime_dependencies.rerank_model_func,
        ollama_server_infos=runtime_dependencies.ollama_server_infos,
    )

    return RagAppRuntime(
        rag=rag,
        rerank_enabled=runtime_dependencies.rerank_model_func is not None,
    )
