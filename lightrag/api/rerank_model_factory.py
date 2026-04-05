from __future__ import annotations

import inspect

from lightrag.utils import logger


def build_rerank_model_func(args):
    """Build the optional rerank model wrapper and fill default rerank args in-place."""
    rerank_model_func = None

    if args.rerank_binding == "null":
        logger.info("Reranking is disabled")
        return None

    from lightrag.rerank import (
        ali_rerank,
        cohere_rerank,
        jina_rerank,
        local_modelscope_rerank,
    )

    rerank_functions = {
        "cohere": cohere_rerank,
        "jina": jina_rerank,
        "aliyun": ali_rerank,
        "modelscope": local_modelscope_rerank,
    }

    selected_rerank_func = rerank_functions.get(args.rerank_binding)
    if not selected_rerank_func:
        logger.error(f"Unsupported rerank binding: {args.rerank_binding}")
        raise ValueError(f"Unsupported rerank binding: {args.rerank_binding}")

    if args.rerank_model is None or args.rerank_binding_host is None:
        sig = inspect.signature(selected_rerank_func)

        if args.rerank_model is None and "model" in sig.parameters:
            default_model = sig.parameters["model"].default
            if default_model != inspect.Parameter.empty:
                args.rerank_model = default_model

        if args.rerank_binding_host is None and "base_url" in sig.parameters:
            default_base_url = sig.parameters["base_url"].default
            if default_base_url != inspect.Parameter.empty:
                args.rerank_binding_host = default_base_url

    async def server_rerank_func(
        query: str, documents: list, top_n: int = None, extra_body: dict = None
    ):
        return await selected_rerank_func(
            query=query,
            documents=documents,
            top_n=top_n,
            extra_body=extra_body,
        )

    rerank_model_func = server_rerank_func
    logger.info(
        f"Reranking is enabled: {args.rerank_model or 'default model'} using {args.rerank_binding} provider"
    )
    return rerank_model_func
