from __future__ import annotations

from lightrag import LightRAG
from lightrag.api.rag_runtime_config import build_rag_kwargs
from lightrag.utils import logger


def build_rag(
    args,
    config_cache,
    llm_timeout: int,
    embedding_timeout: int,
    embedding_func,
    rerank_model_func,
    ollama_server_infos,
    rag_factory=LightRAG,
):
    """Build the runtime LightRAG instance from assembled dependencies."""
    try:
        return rag_factory(
            **build_rag_kwargs(
                args=args,
                config_cache=config_cache,
                llm_timeout=llm_timeout,
                embedding_timeout=embedding_timeout,
                embedding_func=embedding_func,
                rerank_model_func=rerank_model_func,
                ollama_server_infos=ollama_server_infos,
            )
        )
    except Exception as exc:
        logger.error(f"Failed to initialize LightRAG: {exc}")
        raise
