import copy
import os
from functools import lru_cache

import pipmaster as pm  # Pipmaster for dynamic library install

# install specific modules
if not pm.is_installed("transformers"):
    pm.install("transformers")
if not pm.is_installed("torch"):
    pm.install("torch")
if not pm.is_installed("numpy"):
    pm.install("numpy")

from transformers import AutoTokenizer, AutoModelForCausalLM
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
import torch
import numpy as np
from lightrag.utils import wrap_embedding_func_with_attrs

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from modelscope import snapshot_download
@lru_cache(maxsize=1)
def initialize_hf_model(pretrained_model_name_or_path):

    # if not os.path.exists(pretrained_model_name_or_path):
    #     model_dir = snapshot_download(pretrained_model_name_or_path)
    # else:
    #     model_dir = pretrained_model_name_or_path
    hf_tokenizer = AutoTokenizer.from_pretrained(
        pretrained_model_name_or_path, device_map="auto", trust_remote_code=True
    )
    hf_model = AutoModelForCausalLM.from_pretrained(
        pretrained_model_name_or_path, device_map="auto", trust_remote_code=True,
    )
    if hf_tokenizer.pad_token is None:
        hf_tokenizer.pad_token = hf_tokenizer.eos_token

    return hf_model, hf_tokenizer


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (RateLimitError, APIConnectionError, APITimeoutError)
    ),
)
async def hf_model_if_cache(
    model,
    prompt,
    system_prompt=None,
    history_messages=[],
    enable_cot: bool = False,
    **kwargs,
) -> str:
    if enable_cot:
        from lightrag.utils import logger

        logger.debug(
            "enable_cot=True is not supported for Hugging Face local models and will be ignored."
        )
    model_name = model
    model_path = os.getenv("HF_MODEL_PATH","D:\PythonProject\models\qwen3-8b")
    hf_model, hf_tokenizer = initialize_hf_model(model_path)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    kwargs.pop("hashing_kv", None)
    input_prompt = ""
    try:
        input_prompt = hf_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        try:
            ori_message = copy.deepcopy(messages)
            if messages[0]["role"] == "system":
                messages[1]["content"] = (
                    "<system>"
                    + messages[0]["content"]
                    + "</system>\n"
                    + messages[1]["content"]
                )
                messages = messages[1:]
                input_prompt = hf_tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
        except Exception:
            len_message = len(ori_message)
            for msgid in range(len_message):
                input_prompt = (
                    input_prompt
                    + "<"
                    + ori_message[msgid]["role"]
                    + ">"
                    + ori_message[msgid]["content"]
                    + "</"
                    + ori_message[msgid]["role"]
                    + ">\n"
                )

    input_ids = hf_tokenizer(
        input_prompt, return_tensors="pt", padding=True, truncation=True
    ).to("cuda")
    inputs = {k: v.to(hf_model.device) for k, v in input_ids.items()}
    output = hf_model.generate(
        **input_ids, max_new_tokens=512, num_return_sequences=1, early_stopping=True
    )
    response_text = hf_tokenizer.decode(
        output[0][len(inputs["input_ids"][0]) :], skip_special_tokens=True
    )

    return response_text


async def hf_model_complete(
    prompt,
    system_prompt=None,
    history_messages=[],
    keyword_extraction=False,
    enable_cot: bool = False,
    **kwargs,
) -> str:
    kwargs.pop("keyword_extraction", None)
    model_name = kwargs["hashing_kv"].global_config["llm_model_name"]
    result = await hf_model_if_cache(
        model_name,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        enable_cot=enable_cot,
        **kwargs,
    )
    return result


from modelscope import AutoModel, AutoTokenizer
from functools import lru_cache
import torch


@lru_cache(maxsize=1)
def initialize_bge_model_optimized(model_path):
    """
    针对BGE模型的优化初始化，适配你的hf_embed函数

    Args:
        model_path: BGE模型路径

    Returns:
        tokenizer, embed_model
    """
    try:
        # 加载tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )

        # 加载模型
        embed_model = AutoModel.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map="auto"
        )

        # BGE模型建议使用[CLS] pooling而不是mean pooling
        # 但保持与你现有hf_embed函数的兼容性

        embed_model.eval()

        # 打印模型信息
        # param_count = sum(p.numel() for p in embed_model.parameters())
        # print(f"✅ BGE模型加载完成: {model_path}")
        # print(f"📊 参数量: {param_count:,}")
        # print(f"💻 运行设备: {next(embed_model.parameters()).device}")
        # print(f"🔤 Tokenizer类型: {type(tokenizer).__name__}")

        return tokenizer, embed_model

    except Exception as e:
        print(f"❌ BGE模型加载失败: {e}")
        raise


@wrap_embedding_func_with_attrs(embedding_dim=1024, max_token_size=8192)
async def modelscope_embed(texts: list[str], tokenizer, embed_model) -> np.ndarray:
    #print(f"🔍 hf_embed函数开始执行，文本数量: {len(texts)}")

    try:
        # 设备检测
        if torch.cuda.is_available():
            device = next(embed_model.parameters()).device
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

        # print(f"💻 选择的设备: {device}")

        # 移动模型到设备
        embed_model = embed_model.to(device)
        # print("✅ 模型已移动到设备")

        # Tokenize - 正确的方式
        encoded_texts = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        # print("✅ Tokenize完成")

        # 将tensor移动到设备，而不是整个字典
        encoded_texts = {key: value.to(device) for key, value in encoded_texts.items()}
        # print("✅ Tensor已移动到设备")

        # 执行推理
        with torch.no_grad():
            # print("🔄 开始模型推理...")
            outputs = embed_model(
                input_ids=encoded_texts["input_ids"],
                attention_mask=encoded_texts["attention_mask"],
            )
            # print("✅ 模型推理完成")

            # 对于BGE模型，推荐使用mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
            # print("✅ Mean pooling完成")

            # 对嵌入进行归一化（BGE模型推荐）
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            # print("✅ 归一化完成")

        # 转换为numpy
        if embeddings.dtype == torch.bfloat16:
            result = embeddings.detach().to(torch.float32).cpu().numpy()
        else:
            result = embeddings.detach().cpu().numpy()

        # print(f"🎉 嵌入生成成功，形状: {result.shape}")
        return result

    except Exception as e:
        print(f"❌ hf_embed函数内部错误: {e}")
        print(f"📋 错误类型: {type(e).__name__}")
        import traceback
        print(f"🔍 堆栈跟踪: {traceback.format_exc()}")
        raise
