from __future__ import annotations

import os

from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import get_env_value


def _create_optimized_openai_llm_func(config_cache, args, llm_timeout: int):
    """Create optimized OpenAI-compatible LLM function with cached configuration."""

    async def optimized_openai_alike_model_complete(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        from lightrag.llm.openai import openai_complete_if_cache

        keyword_extraction = kwargs.pop("keyword_extraction", None)
        if keyword_extraction:
            kwargs["response_format"] = GPTKeywordExtractionFormat
        if history_messages is None:
            history_messages = []

        kwargs["timeout"] = llm_timeout
        if config_cache.openai_llm_options:
            kwargs.update(config_cache.openai_llm_options)

        return await openai_complete_if_cache(
            args.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            base_url=args.llm_binding_host,
            api_key=args.llm_binding_api_key,
            **kwargs,
        )

    return optimized_openai_alike_model_complete


def _create_optimized_modelscope_llm_func(config_cache, args, llm_timeout: int):
    """Return the existing ModelScope completion callable."""
    del config_cache, args, llm_timeout
    from lightrag.llm.hf import hf_model_complete

    return hf_model_complete


def _create_optimized_azure_openai_llm_func(config_cache, args, llm_timeout: int):
    """Create optimized Azure OpenAI LLM function with cached configuration."""

    async def optimized_azure_openai_model_complete(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        from lightrag.llm.azure_openai import azure_openai_complete_if_cache

        keyword_extraction = kwargs.pop("keyword_extraction", None)
        if keyword_extraction:
            kwargs["response_format"] = GPTKeywordExtractionFormat
        if history_messages is None:
            history_messages = []

        kwargs["timeout"] = llm_timeout
        if config_cache.openai_llm_options:
            kwargs.update(config_cache.openai_llm_options)

        return await azure_openai_complete_if_cache(
            args.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            base_url=args.llm_binding_host,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", args.llm_binding_api_key),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            **kwargs,
        )

    return optimized_azure_openai_model_complete


def _create_optimized_gemini_llm_func(config_cache, args, llm_timeout: int):
    """Create optimized Gemini LLM function with cached configuration."""

    async def optimized_gemini_model_complete(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        from lightrag.llm.gemini import gemini_complete_if_cache

        if history_messages is None:
            history_messages = []

        kwargs["timeout"] = llm_timeout
        if (
            config_cache.gemini_llm_options is not None
            and "generation_config" not in kwargs
        ):
            kwargs["generation_config"] = dict(config_cache.gemini_llm_options)

        return await gemini_complete_if_cache(
            args.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=args.llm_binding_api_key,
            base_url=args.llm_binding_host,
            keyword_extraction=keyword_extraction,
            **kwargs,
        )

    return optimized_gemini_model_complete


def _create_bedrock_llm_func(args):
    """Create the Bedrock LLM callable."""

    async def bedrock_model_complete(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        from lightrag.llm.bedrock import bedrock_complete_if_cache

        keyword_extraction = kwargs.pop("keyword_extraction", None)
        if keyword_extraction:
            kwargs["response_format"] = GPTKeywordExtractionFormat
        if history_messages is None:
            history_messages = []

        kwargs["temperature"] = get_env_value("BEDROCK_LLM_TEMPERATURE", 1.0, float)

        return await bedrock_complete_if_cache(
            args.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    return bedrock_model_complete


def build_llm_model_func(binding: str, config_cache, args, llm_timeout: int):
    """
    Create an LLM model function based on binding type.
    Uses optimized wrappers for OpenAI-compatible bindings and lazy import for others.
    """
    try:
        if binding == "modelscope":
            return _create_optimized_modelscope_llm_func(config_cache, args, llm_timeout)
        if binding == "lollms":
            from lightrag.llm.lollms import lollms_model_complete

            return lollms_model_complete
        if binding == "ollama":
            from lightrag.llm.ollama import ollama_model_complete

            return ollama_model_complete
        if binding == "aws_bedrock":
            return _create_bedrock_llm_func(args)
        if binding == "azure_openai":
            return _create_optimized_azure_openai_llm_func(
                config_cache, args, llm_timeout
            )
        if binding == "gemini":
            return _create_optimized_gemini_llm_func(config_cache, args, llm_timeout)
        return _create_optimized_openai_llm_func(config_cache, args, llm_timeout)
    except ImportError as exc:
        raise Exception(f"Failed to import {binding} LLM binding: {exc}")
