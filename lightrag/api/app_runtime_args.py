from __future__ import annotations

import os

from lightrag.api.config import get_default_host


SUPPORTED_LLM_BINDINGS = (
    "modelscope",
    "lollms",
    "ollama",
    "openai",
    "azure_openai",
    "aws_bedrock",
    "gemini",
)

SUPPORTED_EMBEDDING_BINDINGS = (
    "modelscope",
    "lollms",
    "ollama",
    "openai",
    "azure_openai",
    "aws_bedrock",
    "jina",
    "gemini",
)


def normalize_runtime_args(args):
    """Validate supported runtime bindings and fill required defaults in-place."""

    if args.llm_binding not in SUPPORTED_LLM_BINDINGS:
        raise Exception("llm binding not supported")

    if args.embedding_binding not in SUPPORTED_EMBEDDING_BINDINGS:
        raise Exception("embedding binding not supported")

    if args.llm_binding_host is None:
        args.llm_binding_host = get_default_host(args.llm_binding)

    if args.embedding_binding_host is None:
        args.embedding_binding_host = get_default_host(args.embedding_binding)

    if args.ssl:
        if not args.ssl_certfile or not args.ssl_keyfile:
            raise Exception(
                "SSL certificate and key files must be provided when SSL is enabled"
            )
        if not os.path.exists(args.ssl_certfile):
            raise Exception(f"SSL certificate file not found: {args.ssl_certfile}")
        if not os.path.exists(args.ssl_keyfile):
            raise Exception(f"SSL key file not found: {args.ssl_keyfile}")

    return args
