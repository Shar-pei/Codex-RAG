from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest

from lightrag.kg.chroma_impl import ChromaVectorDBStorage
from lightrag.kg.neo4j_impl import Neo4JStorage
from lightrag.kg.postgres_impl import PGKVStorage
from lightrag.kg.shared_storage import initialize_share_data
from lightrag.kg.storage_contracts import resolve_storage_workspace
from lightrag.namespace import NameSpace
from lightrag.utils import EmbeddingFunc


async def _embedding_func(texts: list[str], **kwargs) -> np.ndarray:
    return np.zeros((len(texts), 3), dtype=np.float32)


def _embedding() -> EmbeddingFunc:
    return EmbeddingFunc(embedding_dim=3, func=_embedding_func)


def _vector_config(tmp_path) -> dict:
    return {
        "working_dir": str(tmp_path),
        "embedding_batch_num": 2,
        "vector_db_storage_cls_kwargs": {
            "cosine_better_than_threshold": 0.1,
        },
    }


def _make_workspace_dir() -> Path:
    temp_root = Path.cwd() / "temp"
    temp_root.mkdir(exist_ok=True)
    return Path(mkdtemp(prefix=f"storage-contracts-{uuid4().hex[:8]}-", dir=temp_root))


@pytest.fixture(autouse=True)
def _clear_workspace_env(monkeypatch):
    for key in ("WORKSPACE", "CHROMA_WORKSPACE", "NEO4J_WORKSPACE"):
        monkeypatch.delenv(key, raising=False)


def test_resolve_storage_workspace_prefers_first_non_empty_candidate():
    resolved = resolve_storage_workspace(
        None,
        "   ",
        " provider-workspace ",
        "fallback-workspace",
        default="default",
    )

    assert resolved == "provider-workspace"


def test_chroma_workspace_contract_prefers_provider_override(monkeypatch):
    monkeypatch.setenv("WORKSPACE", "shared-workspace")
    monkeypatch.setenv("CHROMA_WORKSPACE", "chroma-workspace")
    tmp_path = _make_workspace_dir()

    storage = ChromaVectorDBStorage(
        namespace=NameSpace.VECTOR_STORE_CHUNKS,
        workspace="explicit-workspace",
        global_config=_vector_config(tmp_path),
        embedding_func=_embedding(),
        meta_fields={"full_doc_id"},
    )

    assert storage.workspace == "chroma-workspace"
    assert storage._workspace_name == "chroma-workspace"
    assert storage._collection_name.startswith("chroma-workspace__chunks")


def test_neo4j_workspace_contract_uses_override_and_base_default(monkeypatch):
    monkeypatch.setenv("NEO4J_WORKSPACE", "neo4j-workspace")

    override_storage = Neo4JStorage(
        namespace=NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION,
        workspace="explicit-workspace",
        global_config={},
        embedding_func=_embedding(),
    )

    assert override_storage.workspace == "neo4j-workspace"

    monkeypatch.delenv("NEO4J_WORKSPACE", raising=False)
    default_storage = Neo4JStorage(
        namespace=NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION,
        workspace="   ",
        global_config={},
        embedding_func=_embedding(),
    )

    assert default_storage.workspace == "base"


@pytest.mark.asyncio
async def test_postgres_workspace_contract_prefers_db_workspace():
    initialize_share_data()

    storage = PGKVStorage(
        namespace=NameSpace.KV_STORE_TEXT_CHUNKS,
        workspace="explicit-workspace",
        global_config={"embedding_batch_num": 2},
        embedding_func=_embedding(),
        db=SimpleNamespace(workspace="db-workspace"),
    )

    await storage.initialize()

    assert storage.workspace == "db-workspace"
