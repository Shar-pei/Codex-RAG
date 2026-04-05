from __future__ import annotations


def build_llm_model_kwargs(binding: str, args, llm_timeout: int) -> dict:
    """Build binding-specific LLM kwargs for LightRAG model setup."""
    if binding in ["lollms", "ollama"]:
        try:
            from lightrag.llm.binding_options import OllamaLLMOptions

            return {
                "host": args.llm_binding_host,
                "timeout": llm_timeout,
                "options": OllamaLLMOptions.options_dict(args),
                "api_key": args.llm_binding_api_key,
            }
        except ImportError as exc:
            raise Exception(f"Failed to import {binding} options: {exc}")

    return {}
