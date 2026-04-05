from __future__ import annotations

import inspect

from lightrag.utils import logger


def apply_embedding_dimension_policy(embedding_func, args) -> None:
    """Apply the embedding dimension-delivery policy to an EmbeddingFunc."""
    has_embedding_dim_param = "embedding_dim" in inspect.signature(
        embedding_func.func
    ).parameters

    if args.embedding_binding in ["jina", "gemini"]:
        send_dimensions = has_embedding_dim_param
        dimension_control = f"forced by {args.embedding_binding.title()} API"
    else:
        send_dimensions = args.embedding_send_dim and has_embedding_dim_param
        if send_dimensions or not args.embedding_send_dim:
            dimension_control = "by env var"
        else:
            dimension_control = "by not hasparam"

    embedding_func.send_dimensions = send_dimensions

    logger.info(
        f"Send embedding dimension: {send_dimensions} {dimension_control} "
        f"(dimensions={embedding_func.embedding_dim}, has_param={has_embedding_dim_param}, "
        f"binding={args.embedding_binding})"
    )
