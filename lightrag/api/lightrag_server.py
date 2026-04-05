"""
LightRAG FastAPI Server
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
import os
import logging
import logging.config
import sys
import uvicorn
from pathlib import Path
import configparser
from dotenv import load_dotenv
from lightrag._pipmaster import get_pipmaster
from lightrag.api.app_cors import configure_cors
from lightrag.api.app_factory_config import build_app_kwargs
from lightrag.api.app_lifespan import create_app_lifespan
from lightrag.api.app_runtime_args import normalize_runtime_args
from lightrag.api.frontend_build_checker import check_frontend_build
from lightrag.api.query_validation_handlers import (
    create_query_validation_exception_handler,
)
from lightrag.api.utils_api import display_splash_screen, check_env_file
from .config import (
    global_args,
    update_uvicorn_mode_config,
)
from lightrag.utils import get_env_value
from lightrag import LightRAG
from lightrag.api import __api_version__
from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import EmbeddingFunc
from lightrag.api.app_route_context import RouteRegistryContext
from lightrag.api.route_registry import register_app_routes
from lightrag.constants import (
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILENAME,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_EMBEDDING_TIMEOUT,
)
from lightrag.api.routers.document_routes import DocumentManager

from lightrag.utils import logger, set_verbose_debug

pm = get_pipmaster()

# use the .env that is inside the current folder
# allows to use different .env file for each lightrag instance
# the OS environment variables take precedence over the .env file
load_dotenv(dotenv_path=".env", override=False)


webui_title = os.getenv("WEBUI_TITLE")
webui_description = os.getenv("WEBUI_DESCRIPTION")

# Initialize config parser
config = configparser.ConfigParser()
config.read("config.ini")

class LLMConfigCache:
    """Smart LLM and Embedding configuration cache class"""

    def __init__(self, args):
        self.args = args

        # Initialize configurations based on binding conditions
        self.openai_llm_options = None
        self.gemini_llm_options = None
        self.gemini_embedding_options = None
        self.ollama_llm_options = None
        self.ollama_embedding_options = None

        # Only initialize and log OpenAI options when using OpenAI-related bindings
        if args.llm_binding in ["openai", "azure_openai"]:
            from lightrag.llm.binding_options import OpenAILLMOptions

            self.openai_llm_options = OpenAILLMOptions.options_dict(args)
            logger.info(f"OpenAI LLM Options: {self.openai_llm_options}")

        if args.llm_binding == "gemini":
            from lightrag.llm.binding_options import GeminiLLMOptions

            self.gemini_llm_options = GeminiLLMOptions.options_dict(args)
            logger.info(f"Gemini LLM Options: {self.gemini_llm_options}")

        # Only initialize and log Ollama LLM options when using Ollama LLM binding
        if args.llm_binding == "ollama":
            try:
                from lightrag.llm.binding_options import OllamaLLMOptions

                self.ollama_llm_options = OllamaLLMOptions.options_dict(args)
                logger.info(f"Ollama LLM Options: {self.ollama_llm_options}")
            except ImportError:
                logger.warning(
                    "OllamaLLMOptions not available, using default configuration"
                )
                self.ollama_llm_options = {}

        # Only initialize and log Ollama Embedding options when using Ollama Embedding binding
        if args.embedding_binding == "ollama":
            try:
                from lightrag.llm.binding_options import OllamaEmbeddingOptions

                self.ollama_embedding_options = OllamaEmbeddingOptions.options_dict(
                    args
                )
                logger.info(
                    f"Ollama Embedding Options: {self.ollama_embedding_options}"
                )
            except ImportError:
                logger.warning(
                    "OllamaEmbeddingOptions not available, using default configuration"
                )
                self.ollama_embedding_options = {}

        # Only initialize and log Gemini Embedding options when using Gemini Embedding binding
        if args.embedding_binding == "gemini":
            try:
                from lightrag.llm.binding_options import GeminiEmbeddingOptions

                self.gemini_embedding_options = GeminiEmbeddingOptions.options_dict(
                    args
                )
                logger.info(
                    f"Gemini Embedding Options: {self.gemini_embedding_options}"
                )
            except ImportError:
                logger.warning(
                    "GeminiEmbeddingOptions not available, using default configuration"
                )
                self.gemini_embedding_options = {}
def create_app(args):
    # Check frontend build first and get status
    webui_assets_exist, is_frontend_outdated = check_frontend_build()

    # Create unified API version display with warning symbol if frontend is outdated
    api_version_display = (
        f"{__api_version__}⚠️" if is_frontend_outdated else __api_version__
    )

    # Setup logging
    logger.setLevel(args.log_level)
    set_verbose_debug(args.verbose)

    # Create configuration cache (this will output configuration logs)
    config_cache = LLMConfigCache(args)

    normalize_runtime_args(args)

    # Check if API key is provided either through env var or args
    api_key = os.getenv("LIGHTRAG_API_KEY") or args.key

    # Initialize document manager with workspace support for data isolation
    doc_manager = DocumentManager(args.input_dir, workspace=args.workspace)

    app_kwargs = build_app_kwargs(api_key=api_key, api_version=__api_version__)

    # Create working directory if it doesn't exist
    Path(args.working_dir).mkdir(parents=True, exist_ok=True)

    def create_optimized_openai_llm_func(
        config_cache: LLMConfigCache, args, llm_timeout: int
    ):
        """Create optimized OpenAI LLM function with pre-processed configuration"""

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

            # Use pre-processed configuration to avoid repeated parsing
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
    def create_optimized_modelscope_llm_func(
        config_cache: LLMConfigCache, args, llm_timeout: int
    ):
        """Create optimized OpenAI LLM function with pre-processed configuration"""
        from lightrag.llm.hf import hf_model_complete
        return hf_model_complete
        # async def optimized_openai_alike_model_complete(
        #     prompt,
        #     system_prompt=None,
        #     history_messages=None,
        #     keyword_extraction=False,
        #     **kwargs,
        # ) -> str:
        #     from lightrag.llm.hf import hf_model_complete
        #
        #     keyword_extraction = kwargs.pop("keyword_extraction", None)
        #     if keyword_extraction:
        #         kwargs["response_format"] = GPTKeywordExtractionFormat
        #     if history_messages is None:
        #         history_messages = []
        #
        #     # Use pre-processed configuration to avoid repeated parsing
        #     kwargs["timeout"] = llm_timeout
        #     if config_cache.openai_llm_options:
        #         kwargs.update(config_cache.openai_llm_options)
        #
        #     return await hf_model_complete(
        #         args.llm_model,
        #         prompt,
        #         system_prompt=system_prompt,
        #         history_messages=history_messages,
        #         enable_cot=False,
        #         **kwargs,
        #     )
        #
        # return optimized_openai_alike_model_complete

    def create_optimized_azure_openai_llm_func(
        config_cache: LLMConfigCache, args, llm_timeout: int
    ):
        """Create optimized Azure OpenAI LLM function with pre-processed configuration"""

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

            # Use pre-processed configuration to avoid repeated parsing
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

    def create_optimized_gemini_llm_func(
        config_cache: LLMConfigCache, args, llm_timeout: int
    ):
        """Create optimized Gemini LLM function with cached configuration"""

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

            # Use pre-processed configuration to avoid repeated parsing
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

    def create_llm_model_func(binding: str):
        """
        Create LLM model function based on binding type.
        Uses optimized functions for OpenAI bindings and lazy import for others.
        """
        try:
            if binding == "modelscope":
                return create_optimized_modelscope_llm_func(config_cache, args, llm_timeout)
            elif binding == "lollms":
                from lightrag.llm.lollms import lollms_model_complete

                return lollms_model_complete
            elif binding == "ollama":
                from lightrag.llm.ollama import ollama_model_complete

                return ollama_model_complete
            elif binding == "aws_bedrock":
                return bedrock_model_complete  # Already defined locally
            elif binding == "azure_openai":
                # Use optimized function with pre-processed configuration
                return create_optimized_azure_openai_llm_func(
                    config_cache, args, llm_timeout
                )
            elif binding == "gemini":
                return create_optimized_gemini_llm_func(config_cache, args, llm_timeout)
            else:  # openai and compatible
                # Use optimized function with pre-processed configuration
                return create_optimized_openai_llm_func(config_cache, args, llm_timeout)
        except ImportError as e:
            raise Exception(f"Failed to import {binding} LLM binding: {e}")

    def create_llm_model_kwargs(binding: str, args, llm_timeout: int) -> dict:
        """
        Create LLM model kwargs based on binding type.
        Uses lazy import for binding-specific options.
        """
        if binding in ["lollms", "ollama"]:
            try:
                from lightrag.llm.binding_options import OllamaLLMOptions

                return {
                    "host": args.llm_binding_host,
                    "timeout": llm_timeout,
                    "options": OllamaLLMOptions.options_dict(args),
                    "api_key": args.llm_binding_api_key,
                }
            except ImportError as e:
                raise Exception(f"Failed to import {binding} options: {e}")
        return {}

    def create_optimized_embedding_function(
        config_cache: LLMConfigCache, binding, model, host, api_key, args
    ) -> EmbeddingFunc:
        """
        Create optimized embedding function and return an EmbeddingFunc instance
        with proper max_token_size inheritance from provider defaults.

        This function:
        1. Imports the provider embedding function
        2. Extracts max_token_size and embedding_dim from provider if it's an EmbeddingFunc
        3. Creates an optimized wrapper that calls the underlying function directly (avoiding double-wrapping)
        4. Returns a properly configured EmbeddingFunc instance
        """

        # Step 1: Import provider function and extract default attributes
        provider_func = None
        provider_max_token_size = None
        provider_embedding_dim = None

        try:
            if binding == "openai":
                from lightrag.llm.openai import openai_embed

                provider_func = openai_embed
            elif binding == "ollama":
                from lightrag.llm.ollama import ollama_embed

                provider_func = ollama_embed
            elif binding == "gemini":
                from lightrag.llm.gemini import gemini_embed

                provider_func = gemini_embed
            elif binding == "jina":
                from lightrag.llm.jina import jina_embed

                provider_func = jina_embed
            elif binding == "azure_openai":
                from lightrag.llm.azure_openai import azure_openai_embed

                provider_func = azure_openai_embed
            elif binding == "aws_bedrock":
                from lightrag.llm.bedrock import bedrock_embed

                provider_func = bedrock_embed
            elif binding == "lollms":
                from lightrag.llm.lollms import lollms_embed

                provider_func = lollms_embed
            elif binding == "modelscope":
                from lightrag.llm.hf import modelscope_embed

                provider_func = modelscope_embed

            # Extract attributes if provider is an EmbeddingFunc
            if provider_func and isinstance(provider_func, EmbeddingFunc):
                provider_max_token_size = provider_func.max_token_size
                provider_embedding_dim = provider_func.embedding_dim
                logger.debug(
                    f"Extracted from {binding} provider: "
                    f"max_token_size={provider_max_token_size}, "
                    f"embedding_dim={provider_embedding_dim}"
                )
        except ImportError as e:
            logger.warning(f"Could not import provider function for {binding}: {e}")

        # Step 2: Apply priority (user config > provider default)
        # For max_token_size: explicit env var > provider default > None
        final_max_token_size = args.embedding_token_limit or provider_max_token_size
        # For embedding_dim: user config (always has value) takes priority
        # Only use provider default if user config is explicitly None (which shouldn't happen)
        final_embedding_dim = (
            args.embedding_dim if args.embedding_dim else provider_embedding_dim
        )

        # Step 3: Create optimized embedding function (calls underlying function directly)
        async def optimized_embedding_function(texts, embedding_dim=None):
            try:
                if binding == "lollms":
                    from lightrag.llm.lollms import lollms_embed

                    # Get real function, skip EmbeddingFunc wrapper if present
                    actual_func = (
                        lollms_embed.func
                        if isinstance(lollms_embed, EmbeddingFunc)
                        else lollms_embed
                    )
                    return await actual_func(
                        texts, embed_model=model, host=host, api_key=api_key
                    )
                elif binding == "ollama":
                    from lightrag.llm.ollama import ollama_embed

                    # Get real function, skip EmbeddingFunc wrapper if present
                    actual_func = (
                        ollama_embed.func
                        if isinstance(ollama_embed, EmbeddingFunc)
                        else ollama_embed
                    )

                    # Use pre-processed configuration if available
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
                elif binding == "azure_openai":
                    from lightrag.llm.azure_openai import azure_openai_embed

                    actual_func = (
                        azure_openai_embed.func
                        if isinstance(azure_openai_embed, EmbeddingFunc)
                        else azure_openai_embed
                    )
                    return await actual_func(texts, model=model, api_key=api_key)
                elif binding == "aws_bedrock":
                    from lightrag.llm.bedrock import bedrock_embed

                    actual_func = (
                        bedrock_embed.func
                        if isinstance(bedrock_embed, EmbeddingFunc)
                        else bedrock_embed
                    )
                    return await actual_func(texts, model=model)
                elif binding == "jina":
                    from lightrag.llm.jina import jina_embed

                    actual_func = (
                        jina_embed.func
                        if isinstance(jina_embed, EmbeddingFunc)
                        else jina_embed
                    )
                    return await actual_func(
                        texts,
                        embedding_dim=embedding_dim,
                        base_url=host,
                        api_key=api_key,
                    )
                elif binding == "gemini":
                    from lightrag.llm.gemini import gemini_embed

                    actual_func = (
                        gemini_embed.func
                        if isinstance(gemini_embed, EmbeddingFunc)
                        else gemini_embed
                    )

                    # Use pre-processed configuration if available
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
                elif binding ==  "openai":
                # openai and compatible
                    from lightrag.llm.openai import openai_embed

                    actual_func = (
                        openai_embed.func
                        if isinstance(openai_embed, EmbeddingFunc)
                        else openai_embed
                    )
                    return await actual_func(
                        texts,
                        model=model,
                        base_url=host,
                        api_key=api_key,
                        embedding_dim=embedding_dim,
                    )
                else:
                    from lightrag.llm.hf import modelscope_embed,initialize_bge_model_optimized
                    actual_func = (
                        modelscope_embed.func
                        if isinstance(modelscope_embed, EmbeddingFunc)
                        else modelscope_embed
                    )
                    model_path = os.getenv(r"HF_EMBEDDING_MODEL_PATH", r"D:\PythonProject\models\bge-large-zh-v1.5")
                    modelscope_tokenizer,modelscope_model = initialize_bge_model_optimized(model_path)
                    return await actual_func(
                        texts,
                        tokenizer=modelscope_tokenizer,
                        embed_model=modelscope_model
                    )
            except ImportError as e:
                raise Exception(f"Failed to import {binding} embedding: {e}")

        # Step 4: Wrap in EmbeddingFunc and return
        embedding_func_instance = EmbeddingFunc(
            embedding_dim=final_embedding_dim,
            func=optimized_embedding_function,
            max_token_size=final_max_token_size,
            send_dimensions=False,  # Will be set later based on binding requirements
        )

        # Log final embedding configuration
        logger.info(
            f"Embedding config: binding={binding} model={model} "
            f"embedding_dim={final_embedding_dim} max_token_size={final_max_token_size}"
        )

        return embedding_func_instance

    llm_timeout = get_env_value("LLM_TIMEOUT", DEFAULT_LLM_TIMEOUT, int)
    embedding_timeout = get_env_value(
        "EMBEDDING_TIMEOUT", DEFAULT_EMBEDDING_TIMEOUT, int
    )

    async def bedrock_model_complete(
        prompt,
        system_prompt=None,
        history_messages=None,
        keyword_extraction=False,
        **kwargs,
    ) -> str:
        # Lazy import
        from lightrag.llm.bedrock import bedrock_complete_if_cache

        keyword_extraction = kwargs.pop("keyword_extraction", None)
        if keyword_extraction:
            kwargs["response_format"] = GPTKeywordExtractionFormat
        if history_messages is None:
            history_messages = []

        # Use global temperature for Bedrock
        kwargs["temperature"] = get_env_value("BEDROCK_LLM_TEMPERATURE", 1.0, float)

        return await bedrock_complete_if_cache(
            args.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            **kwargs,
        )

    # Create embedding function with optimized configuration and max_token_size inheritance
    import inspect

    # Create the EmbeddingFunc instance (now returns complete EmbeddingFunc with max_token_size)
    embedding_func = create_optimized_embedding_function(
        config_cache=config_cache,
        binding=args.embedding_binding,
        model=args.embedding_model,
        host=args.embedding_binding_host,
        api_key=args.embedding_binding_api_key,
        args=args,
    )

    # Get embedding_send_dim from centralized configuration
    embedding_send_dim = args.embedding_send_dim

    # Check if the underlying function signature has embedding_dim parameter
    sig = inspect.signature(embedding_func.func)
    has_embedding_dim_param = "embedding_dim" in sig.parameters

    # Determine send_dimensions value based on binding type
    # Jina and Gemini REQUIRE dimension parameter (forced to True)
    # OpenAI and others: controlled by EMBEDDING_SEND_DIM environment variable
    if args.embedding_binding in ["jina", "gemini"]:
        # Jina and Gemini APIs require dimension parameter - always send it
        send_dimensions = has_embedding_dim_param
        dimension_control = f"forced by {args.embedding_binding.title()} API"
    else:
        # For OpenAI and other bindings, respect EMBEDDING_SEND_DIM setting
        send_dimensions = embedding_send_dim and has_embedding_dim_param
        if send_dimensions or not embedding_send_dim:
            dimension_control = "by env var"
        else:
            dimension_control = "by not hasparam"

    # Set send_dimensions on the EmbeddingFunc instance
    embedding_func.send_dimensions = send_dimensions

    logger.info(
        f"Send embedding dimension: {send_dimensions} {dimension_control} "
        f"(dimensions={embedding_func.embedding_dim}, has_param={has_embedding_dim_param}, "
        f"binding={args.embedding_binding})"
    )

    # Log max_token_size source
    if embedding_func.max_token_size:
        source = (
            "env variable"
            if args.embedding_token_limit
            else f"{args.embedding_binding} provider default"
        )
        logger.info(
            f"Embedding max_token_size: {embedding_func.max_token_size} (from {source})"
        )
    else:
        logger.info("Embedding max_token_size: not set (90% token warning disabled)")

    # Configure rerank function based on args.rerank_bindingparameter
    rerank_model_func = None
    if args.rerank_binding != "null":
        from lightrag.rerank import cohere_rerank, jina_rerank, ali_rerank,local_modelscope_rerank

        # Map rerank binding to corresponding function
        rerank_functions = {
            "cohere": cohere_rerank,
            "jina": jina_rerank,
            "aliyun": ali_rerank,
            "modelscope": local_modelscope_rerank,
        }

        # Select the appropriate rerank function based on binding
        selected_rerank_func = rerank_functions.get(args.rerank_binding)
        if not selected_rerank_func:
            logger.error(f"Unsupported rerank binding: {args.rerank_binding}")
            raise ValueError(f"Unsupported rerank binding: {args.rerank_binding}")

        # Get default values from selected_rerank_func if args values are None
        if args.rerank_model is None or args.rerank_binding_host is None:
            sig = inspect.signature(selected_rerank_func)

            # Set default model if args.rerank_model is None
            if args.rerank_model is None and "model" in sig.parameters:
                default_model = sig.parameters["model"].default
                if default_model != inspect.Parameter.empty:
                    args.rerank_model = default_model

            # Set default base_url if args.rerank_binding_host is None
            if args.rerank_binding_host is None and "base_url" in sig.parameters:
                default_base_url = sig.parameters["base_url"].default
                if default_base_url != inspect.Parameter.empty:
                    args.rerank_binding_host = default_base_url

        async def server_rerank_func(
            query: str, documents: list, top_n: int = None, extra_body: dict = None
        ):
            """Server rerank function with configuration from environment variables"""
            return await selected_rerank_func(
                query=query,
                documents=documents,
                top_n=top_n,
                # api_key=args.rerank_binding_api_key,
                # model=args.rerank_model,
                # base_url=args.rerank_binding_host,
                extra_body=extra_body,
            )

        rerank_model_func = server_rerank_func
        logger.info(
            f"Reranking is enabled: {args.rerank_model or 'default model'} using {args.rerank_binding} provider"
        )
    else:
        logger.info("Reranking is disabled")

    # Create ollama_server_infos from command line arguments
    from lightrag.api.config import OllamaServerInfos

    ollama_server_infos = OllamaServerInfos(
        name=args.simulated_model_name, tag=args.simulated_model_tag
    )

    # Initialize RAG with unified configuration
    try:
        rag = LightRAG(
            working_dir=args.working_dir,
            workspace=args.workspace,
            llm_model_func=create_llm_model_func(args.llm_binding),
            llm_model_name=args.llm_model,
            llm_model_max_async=args.max_async,
            summary_max_tokens=args.summary_max_tokens,
            summary_context_size=args.summary_context_size,
            chunk_token_size=int(args.chunk_size),
            chunk_overlap_token_size=int(args.chunk_overlap_size),
            # chunking_func=lambda tk, content, sc, sc_only, overlap, size:
            #     semantic_chunking_by_token_size(tk, content, overlap, size),
            llm_model_kwargs=create_llm_model_kwargs(
                args.llm_binding, args, llm_timeout
            ),
            embedding_func=embedding_func,
            default_llm_timeout=llm_timeout,
            default_embedding_timeout=embedding_timeout,
            kv_storage=args.kv_storage,
            graph_storage=args.graph_storage,
            vector_storage=args.vector_storage,
            doc_status_storage=args.doc_status_storage,
            vector_db_storage_cls_kwargs={
                "cosine_better_than_threshold": args.cosine_threshold
            },
            enable_llm_cache_for_entity_extract=args.enable_llm_cache_for_extract,
            enable_llm_cache=args.enable_llm_cache,
            rerank_model_func=rerank_model_func,
            max_parallel_insert=args.max_parallel_insert,
            max_graph_nodes=args.max_graph_nodes,
            addon_params={
                "language": args.summary_language,
                "entity_types": args.entity_types,
            },
            ollama_server_infos=ollama_server_infos,
        )
    except Exception as e:
        logger.error(f"Failed to initialize LightRAG: {e}")
        raise

    app = FastAPI(lifespan=create_app_lifespan(rag), **app_kwargs)

    app.exception_handler(RequestValidationError)(
        create_query_validation_exception_handler()
    )

    configure_cors(app, global_args.cors_origins)

    from lightrag.api.auth import auth_handler

    register_app_routes(
        app,
        RouteRegistryContext(
            rag=rag,
            doc_manager=doc_manager,
            api_key=api_key,
            args=args,
            api_version_display=api_version_display,
            webui_assets_exist=webui_assets_exist,
            webui_title=webui_title,
            webui_description=webui_description,
            rerank_enabled=rerank_model_func is not None,
            auth_handler=auth_handler,
        ),
    )

    return app


def get_application(args=None):
    """Factory function for creating the FastAPI application"""
    if args is None:
        args = global_args
    return create_app(args)


def configure_logging():
    """Configure logging for uvicorn startup"""

    # Reset any existing handlers to ensure clean configuration
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "lightrag"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.filters = []

    # Get log directory path from environment variable
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, DEFAULT_LOG_FILENAME))

    print(f"\nLightRAG log file: {log_file_path}\n")
    os.makedirs(os.path.dirname(log_dir), exist_ok=True)

    # Get log file max size and backup count from environment variables
    log_max_bytes = get_env_value("LOG_MAX_BYTES", DEFAULT_LOG_MAX_BYTES, int)
    log_backup_count = get_env_value("LOG_BACKUP_COUNT", DEFAULT_LOG_BACKUP_COUNT, int)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname)s: %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "formatter": "detailed",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                # Configure all uvicorn related loggers
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                    "filters": ["path_filter"],
                },
                "uvicorn.error": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                    "filters": ["path_filter"],
                },
            },
            "filters": {
                "path_filter": {
                    "()": "lightrag.utils.LightragPathFilter",
                },
            },
        }
    )


def check_and_install_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        "uvicorn",
        "tiktoken",
        "fastapi",
        # Add other required packages here
    ]

    for package in required_packages:
        if not pm.is_installed(package):
            print(f"Installing {package}...")
            pm.install(package)
            print(f"{package} installed successfully")


def main():
    # Explicitly initialize configuration for clarity
    # (The proxy will auto-initialize anyway, but this makes intent clear)
    from .config import initialize_config

    initialize_config()

    # Check if running under Gunicorn
    if "GUNICORN_CMD_ARGS" in os.environ:
        # If started with Gunicorn, return directly as Gunicorn will call get_application
        print("Running under Gunicorn - worker management handled by Gunicorn")
        return

    # Check .env file
    if not check_env_file():
        sys.exit(1)

    # Check and install dependencies
    check_and_install_dependencies()

    from multiprocessing import freeze_support

    freeze_support()

    # Configure logging before parsing args
    configure_logging()
    update_uvicorn_mode_config()
    display_splash_screen(global_args)

    # Note: Signal handlers are NOT registered here because:
    # - Uvicorn has built-in signal handling that properly calls lifespan shutdown
    # - Custom signal handlers can interfere with uvicorn's graceful shutdown
    # - Cleanup is handled by the lifespan context manager's finally block

    # Create application instance directly instead of using factory function
    app = create_app(global_args)

    # Start Uvicorn in single process mode
    uvicorn_config = {
        "app": app,  # Pass application instance directly instead of string path
        "host": global_args.host,
        "port": global_args.port,
        "log_config": None,  # Disable default config
    }

    if global_args.ssl:
        uvicorn_config.update(
            {
                "ssl_certfile": global_args.ssl_certfile,
                "ssl_keyfile": global_args.ssl_keyfile,
            }
        )

    print(
        f"Starting Uvicorn server in single-process mode on {global_args.host}:{global_args.port}"
    )
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()
