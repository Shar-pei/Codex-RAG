"""Local embedding model implementation for LightRAG using HuggingFace embedding models."""
import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from functools import lru_cache
import pipmaster as pm

# install specific modules
if not pm.is_installed("transformers"):
    pm.install("transformers")
if not pm.is_installed("torch"):
    pm.install("torch")

from lightrag.utils import wrap_embedding_func_with_attrs, logger


@lru_cache(maxsize=1)
def initialize_local_embedding_model(model_name_or_path: str):
    """Initialize the local embedding model and tokenizer."""
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=True
        )
        model = AutoModel.from_pretrained(
            model_name_or_path,
            trust_remote_code=True,
            device_map="auto"
        )
        return model, tokenizer
    except Exception as e:
        logger.error(f"Failed to initialize local embedding model from {model_name_or_path}: {e}")
        raise


@wrap_embedding_func_with_attrs(embedding_dim=1024, max_token_size=8192)
async def local_embedding(
    texts: list[str], 
    model_name: str = None,
    **kwargs
) -> np.ndarray:
    """Local embedding function using HuggingFace models."""
    # Get model path from environment or use provided model parameter
    if not model_name:
        model_name = os.getenv("LOCAL_EMBEDDING_PATH", "D:\\PythonProject\\models\\bge-large-zh-v1.5")
    
    # Initialize model and tokenizer
    embed_model, tokenizer = initialize_local_embedding_model(model_name)
    
    # Detect the appropriate device
    if torch.cuda.is_available():
        device = next(embed_model.parameters()).device  # Use CUDA if available
    elif torch.backends.mps.is_available():
        device = torch.device("mps")  # Use MPS for Apple Silicon
    else:
        device = torch.device("cpu")  # Fallback to CPU

    # Move the model to the detected device
    embed_model = embed_model.to(device)

    # Process texts in batches to avoid memory issues
    all_embeddings = []
    
    # Process each text individually to handle varying lengths
    for text in texts:
        # Tokenize the input text and move to the same device
        encoded_input = tokenizer(
            text, 
            padding=True, 
            truncation=True, 
            return_tensors='pt',
            max_length=kwargs.get("max_length", 512)
        ).to(device)
        
        # Compute embeddings
        with torch.no_grad():
            model_output = embed_model(**encoded_input)
            # Use the last hidden state and take the mean of the sequence
            sentence_embeddings = model_output.last_hidden_state.mean(dim=1)
        
        # Normalize embeddings (important for BGE models)
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        
        # Convert to numpy and add to the list
        all_embeddings.append(sentence_embeddings.cpu().numpy())
    
    # Concatenate all embeddings
    embeddings_array = np.concatenate(all_embeddings, axis=0)
    
    return embeddings_array


def get_local_embedding_model_path():
    """Get the local embedding model path from environment or use default."""
    default_path = "D:\\PythonProject\\models\\bge-large-zh-v1.5"
    return os.getenv("LOCAL_EMBEDDING_PATH", default_path)