from __future__ import annotations

from dataclasses import dataclass

from lightrag.constants import DEFAULT_EMBEDDING_TIMEOUT, DEFAULT_LLM_TIMEOUT
from lightrag.utils import get_env_value


@dataclass(frozen=True)
class RuntimeModelTimeouts:
    llm_timeout: int
    embedding_timeout: int


def build_runtime_model_timeouts() -> RuntimeModelTimeouts:
    """Load the runtime timeout configuration for LLM and embedding calls."""
    return RuntimeModelTimeouts(
        llm_timeout=get_env_value("LLM_TIMEOUT", DEFAULT_LLM_TIMEOUT, int),
        embedding_timeout=get_env_value(
            "EMBEDDING_TIMEOUT", DEFAULT_EMBEDDING_TIMEOUT, int
        ),
    )
