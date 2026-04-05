from __future__ import annotations

import os

from lightrag.utils import EmbeddingFunc, logger


def _load_provider_embedding(binding: str):
    if binding == "openai":
        from lightrag.llm.openai import openai_embed

        return openai_embed
    if binding == "ollama":
        from lightrag.llm.ollama import ollama_embed

        return ollama_embed
    if binding == "gemini":
        from lightrag.llm.gemini import gemini_embed

        return gemini_embed
    if binding == "jina":
        from lightrag.llm.jina import jina_embed

        return jina_embed
    if binding == "azure_openai":
        from lightrag.llm.azure_openai import azure_openai_embed

        return azure_openai_embed
    if binding == "aws_bedrock":
        from lightrag.llm.bedrock import bedrock_embed

        return bedrock_embed
    if binding == "lollms":
        from lightrag.llm.lollms import lollms_embed

        return lollms_embed
    if binding == "modelscope":
        from lightrag.llm.hf import modelscope_embed

        return modelscope_embed
    return None


def _resolve_provider_embedding_defaults(binding: str):
    provider_max_token_size = None
    provider_embedding_dim = None

    try:
        provider_func = _load_provider_embedding(binding)
        if provider_func and isinstance(provider_func, EmbeddingFunc):
            provider_max_token_size = provider_func.max_token_size
            provider_embedding_dim = provider_func.embedding_dim
            logger.debug(
                f"Extracted from {binding} provider: "
                f"max_token_size={provider_max_token_size}, "
                f"embedding_dim={provider_embedding_dim}"
            )
    except ImportError as exc:
        logger.warning(f"Could not import provider function for {binding}: {exc}")

    return provider_max_token_size, provider_embedding_dim


def _unwrap_embedding_callable(provider_func):
    if isinstance(provider_func, EmbeddingFunc):
        return provider_func.func
    return provider_func


def build_embedding_func(config_cache, binding, model, host, api_key, args) -> EmbeddingFunc:
    """
    Create the configured EmbeddingFunc with provider defaults and optimized dispatch.
    """
    provider_max_token_size, provider_embedding_dim = (
        _resolve_provider_embedding_defaults(binding)
    )

    final_max_token_size = args.embedding_token_limit or provider_max_token_size
    final_embedding_dim = (
        args.embedding_dim if args.embedding_dim else provider_embedding_dim
    )

    async def optimized_embedding_function(texts, embedding_dim=None):
        try:
            if binding == "lollms":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("lollms")
                )
                return await actual_func(
                    texts, embed_model=model, host=host, api_key=api_key
                )

            if binding == "ollama":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("ollama")
                )
                if config_cache.ollama_embedding_options is not None:
                    ollama_options = config_cache.ollama_embedding_options
                else:
                    from lightrag.llm.binding_options import OllamaEmbeddingOptions

                    ollama_options = OllamaEmbeddingOptions.options_dict(args)

                return await actual_func(
                    texts,
                    embed_model=model,
                    host=host,
                    api_key=api_key,
                    options=ollama_options,
                )

            if binding == "azure_openai":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("azure_openai")
                )
                return await actual_func(texts, model=model, api_key=api_key)

            if binding == "aws_bedrock":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("aws_bedrock")
                )
                return await actual_func(texts, model=model)

            if binding == "jina":
                actual_func = _unwrap_embedding_callable(_load_provider_embedding("jina"))
                return await actual_func(
                    texts,
                    embedding_dim=embedding_dim,
                    base_url=host,
                    api_key=api_key,
                )

            if binding == "gemini":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("gemini")
                )
                if config_cache.gemini_embedding_options is not None:
                    gemini_options = config_cache.gemini_embedding_options
                else:
                    from lightrag.llm.binding_options import GeminiEmbeddingOptions

                    gemini_options = GeminiEmbeddingOptions.options_dict(args)

                return await actual_func(
                    texts,
                    model=model,
                    base_url=host,
                    api_key=api_key,
                    embedding_dim=embedding_dim,
                    task_type=gemini_options.get("task_type", "RETRIEVAL_DOCUMENT"),
                )

            if binding == "openai":
                actual_func = _unwrap_embedding_callable(
                    _load_provider_embedding("openai")
                )
                return await actual_func(
                    texts,
                    model=model,
                    base_url=host,
                    api_key=api_key,
                    embedding_dim=embedding_dim,
                )

            from lightrag.llm.hf import (
                initialize_bge_model_optimized,
                modelscope_embed,
            )

            actual_func = _unwrap_embedding_callable(modelscope_embed)
            model_path = os.getenv(
                r"HF_EMBEDDING_MODEL_PATH",
                r"D:\PythonProject\models\bge-large-zh-v1.5",
            )
            modelscope_tokenizer, modelscope_model = initialize_bge_model_optimized(
                model_path
            )
            return await actual_func(
                texts,
                tokenizer=modelscope_tokenizer,
                embed_model=modelscope_model,
            )
        except ImportError as exc:
            raise Exception(f"Failed to import {binding} embedding: {exc}")

    embedding_func_instance = EmbeddingFunc(
        embedding_dim=final_embedding_dim,
        func=optimized_embedding_function,
        max_token_size=final_max_token_size,
        send_dimensions=False,
    )

    logger.info(
        f"Embedding config: binding={binding} model={model} "
        f"embedding_dim={final_embedding_dim} max_token_size={final_max_token_size}"
    )
    return embedding_func_instance
