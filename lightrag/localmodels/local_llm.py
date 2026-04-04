"""Local LLM model implementation for LightRAG using HuggingFace models."""
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from functools import lru_cache
import pipmaster as pm

# install specific modules
if not pm.is_installed("transformers"):
    pm.install("transformers")
if not pm.is_installed("torch"):
    pm.install("torch")

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from lightrag.exceptions import (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)
from lightrag.utils import logger


@lru_cache(maxsize=1)
def initialize_local_model(model_name_or_path: str):
    """Initialize the local model and tokenizer."""
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=True,
            local_files_only=True  # 只使用本地文件
        )

        # 根据是否有GPU来配置device_map
        if torch.cuda.is_available():
            model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path,
                trust_remote_code=True,
                torch_dtype=torch.float16,
                device_map="auto",
                local_files_only=True
            )
        else:
            # CPU模式下使用内存优化
            model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path,
                trust_remote_code=True,
                torch_dtype=torch.float32,  # CPU使用float32
                low_cpu_mem_usage=True,
                local_files_only=True
            )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to initialize local model from {model_name_or_path}: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (RateLimitError, APIConnectionError, APITimeoutError)
    ),
)
async def local_llm_model_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=[],
    enable_cot: bool = False,
    **kwargs,
) -> str:
    """Local LLM model implementation."""
    if enable_cot:
        logger.debug(
            "enable_cot=True is not supported for local models and will be ignored."
        )
    
    # Get model path from environment or use provided model parameter
    model_path = os.getenv("LOCAL_LLM_PATH", model)
    if not model_path or model_path == "local":
        # Default to the model downloaded in D:\PythonProject\models
        model_path = "D:\\PythonProject\\models\\qwen3-8b"
    
    # Initialize model and tokenizer
    hf_model, hf_tokenizer = initialize_local_model(model_path)
    
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    
    # Remove LightRAG-specific kwargs
    kwargs.pop("hashing_kv", None)
    kwargs.pop("keyword_extraction", None)
    
    try:
        # Format the conversation for the model
        input_prompt = hf_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        # Tokenize input
        inputs = hf_tokenizer(
            input_prompt, 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=kwargs.get("max_input_tokens", 8192)
        )
        
        # Move inputs to the same device as the model
        device = next(hf_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            outputs = hf_model.generate(
                **inputs,
                max_new_tokens=kwargs.get("max_tokens", 512),
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.9),
                do_sample=True,
                pad_token_id=hf_tokenizer.eos_token_id
            )
        
        # Decode response
        response_text = hf_tokenizer.decode(
            outputs[0][len(inputs["input_ids"][0]):], 
            skip_special_tokens=True
        )
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in local LLM call: {e}")
        raise


async def local_llm_complete(
    prompt,
    system_prompt=None,
    history_messages=[],
    keyword_extraction=False,
    enable_cot: bool = False,
    **kwargs,
) -> str:
    """Complete function for local LLM."""
    # Get the model name from the global config
    model_name = kwargs.get("hashing_kv", {}).global_config.get("llm_model_name", "local")
    return await local_llm_model_if_cache(
        model_name,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        enable_cot=enable_cot,
        **kwargs,
    )