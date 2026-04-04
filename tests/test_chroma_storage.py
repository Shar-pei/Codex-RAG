from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

import numpy as np
import pytest

from lightrag.kg.chroma_impl import ChromaVectorDBStorage
from lightrag.kg.shared_storage import initialize_share_data
from lightrag.namespace import NameSpace
from lightrag.utils import EmbeddingFunc


def _global_config(tmp_path: Path) -> dict:
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
    return Path(mkdtemp(prefix=f"chroma-test-{uuid4().hex[:8]}-", dir=temp_root))


@pytest.mark.asyncio
async def test_chroma_uses_precomputed_vectors_and_query_embedding():
    initialize_share_data()
    embed_call_count = 0

    async def embedding_func(texts: list[str], **kwargs) -> np.ndarray:
        nonlocal embed_call_count
        embed_call_count += 1
        return np.zeros((len(texts), 3), dtype=np.float32)

    tmp_dir = _make_workspace_dir()
    try:
        storage = ChromaVectorDBStorage(
            namespace=NameSpace.VECTOR_STORE_CHUNKS,
            workspace="workspace_a",
            global_config=_global_config(tmp_dir),
            embedding_func=EmbeddingFunc(embedding_dim=3, func=embedding_func),
            meta_fields={"full_doc_id", "file_path"},
        )
        await storage.initialize()

        try:
            await storage.upsert(
                {
                    "chunk-1": {
                        "content": "alpha",
                        "full_doc_id": "doc-1",
                        "file_path": "alpha.md",
                        "__vector__": np.array([1.0, 0.0, 0.0], dtype=np.float32),
                    },
                    "chunk-2": {
                        "content": "beta",
                        "full_doc_id": "doc-2",
                        "file_path": "beta.md",
                        "__vector__": np.array([0.0, 1.0, 0.0], dtype=np.float32),
                    },
                }
            )

            assert embed_call_count == 0

            results = await storage.query(
                query="ignored",
                top_k=1,
                query_embedding=[1.0, 0.0, 0.0],
            )
            assert embed_call_count == 0
            assert len(results) == 1
            assert results[0]["id"] == "chunk-1"

            by_id = await storage.get_by_id("chunk-1")
            assert by_id is not None
            assert by_id["file_path"] == "alpha.md"

            ordered = await storage.get_by_ids(["chunk-1", "missing"])
            assert ordered[0]["id"] == "chunk-1"
            assert ordered[1] is None

            vectors = await storage.get_vectors_by_ids(["chunk-1", "missing"])
            assert set(vectors.keys()) == {"chunk-1"}
            assert len(vectors["chunk-1"]) == 3

            await storage.delete(["chunk-2"])
            assert await storage.get_by_id("chunk-2") is None

            drop_result = await storage.drop()
            assert drop_result["status"] == "success"
            assert storage._collection.count() == 0
        finally:
            await storage.finalize()
    finally:
        pass


@pytest.mark.asyncio
async def test_chroma_workspace_isolation():
    initialize_share_data()

    async def embedding_func(texts: list[str], **kwargs) -> np.ndarray:
        vectors = []
        for text in texts:
            if text == "alpha":
                vectors.append([1.0, 0.0, 0.0])
            else:
                vectors.append([0.0, 1.0, 0.0])
        return np.array(vectors, dtype=np.float32)

    tmp_dir = _make_workspace_dir()
    try:
        workspace_a = ChromaVectorDBStorage(
            namespace=NameSpace.VECTOR_STORE_ENTITIES,
            workspace="workspace_a",
            global_config=_global_config(tmp_dir),
            embedding_func=EmbeddingFunc(embedding_dim=3, func=embedding_func),
            meta_fields={"entity_name", "source_id", "file_path"},
        )
        workspace_b = ChromaVectorDBStorage(
            namespace=NameSpace.VECTOR_STORE_ENTITIES,
            workspace="workspace_b",
            global_config=_global_config(tmp_dir),
            embedding_func=EmbeddingFunc(embedding_dim=3, func=embedding_func),
            meta_fields={"entity_name", "source_id", "file_path"},
        )

        await workspace_a.initialize()
        await workspace_b.initialize()

        try:
            await workspace_a.upsert(
                {
                    "ent-1": {
                        "content": "alpha",
                        "entity_name": "alpha",
                        "source_id": "chunk-1",
                        "file_path": "a.md",
                    }
                }
            )
            await workspace_b.upsert(
                {
                    "ent-1": {
                        "content": "beta",
                        "entity_name": "beta",
                        "source_id": "chunk-2",
                        "file_path": "b.md",
                    }
                }
            )

            assert workspace_a._collection.name != workspace_b._collection.name

            results_a = await workspace_a.query("alpha", top_k=1)
            results_b = await workspace_b.query("beta", top_k=1)

            assert results_a[0]["file_path"] == "a.md"
            assert results_b[0]["file_path"] == "b.md"
        finally:
            await workspace_b.finalize()
            await workspace_a.finalize()
    finally:
        pass
