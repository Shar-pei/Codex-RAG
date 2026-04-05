from __future__ import annotations

from lightrag.api.config import OllamaServerInfos


def build_ollama_server_infos(args) -> OllamaServerInfos:
    """Build the Ollama-compatible model metadata object from runtime args."""
    return OllamaServerInfos(
        name=args.simulated_model_name,
        tag=args.simulated_model_tag,
    )
