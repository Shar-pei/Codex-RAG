import asyncio
import os
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
from functools import lru_cache

from lightrag.api.lightrag_server import create_app
from lightrag.api.config import initialize_config
from lightrag.utils import EmbeddingFunc, wrap_embedding_func_with_attrs


# 配置本地模型路径
LOCAL_EMBEDDING_MODEL_PATH = os.getenv("LOCAL_EMBEDDING_PATH", "D:/PythonProject/models/bge-large-zh-v1.5")


@lru_cache(maxsize=1)
def load_local_hf_model(model_path):
    """加载本地 HuggingFace 模型（带缓存）"""
    print(f"Loading HuggingFace embedding model from: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_path, trust_remote_code=True)
    return model, tokenizer


@wrap_embedding_func_with_attrs(
embedding_dim=1024,  # 根据您的模型调整
max_token_size=512,  # 根据您的模型调整
send_dimensions=False
)
async def local_hf_embedding_func(texts: list[str]) -> np.ndarray:
    """本地 HuggingFace 嵌入函数"""
    embed_model, tokenizer = load_local_hf_model(LOCAL_EMBEDDING_MODEL_PATH)

    # 检测设备
    device = torch.device("cuda" if torch.cuda.is_available() else
                      "mps" if torch.backends.mps.is_available() else
                     "cpu")

    embed_model = embed_model.to(device)

    # 分词
    encoded = tokenizer(
     texts,
     padding=True,
     truncation=True,
     return_tensors='pt',
     max_length=512
    ).to(device)

    # 推理
    with torch.no_grad():
     outputs = embed_model(**encoded)
    # 使用平均池化或 [CLS] token
     embeddings = outputs.last_hidden_state.mean(dim=1)
    # BGE 模型建议进行 L2 归一化
     embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

    return embeddings.cpu().numpy()


def create_hf_config():
    """创建使用本地 HF 模型的配置"""
    # 设置环境变量来指定使用本地模型
    os.environ["EMBEDDING_BINDING"] = "ollama"  # 临时使用 ollama 绑定
    os.environ["EMBEDDING_MODEL"] = "local-hf-model"  # 模型名称（仅用于标识）
    os.environ["EMBEDDING_DIM"] = "1024"  # 根据实际模型调整

    # 初始化配置
    args = initialize_config()
    return args
