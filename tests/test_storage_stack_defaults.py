from __future__ import annotations

import pytest

from lightrag import LightRAG
from lightrag.api.config import DefaultRAGStorageConfig
from lightrag.kg import STORAGES, STORAGE_IMPLEMENTATIONS, verify_storage_implementation
from lightrag.kg.postgres_impl import PostgreSQLDB


def _postgres_config(**overrides) -> dict[str, object]:
    config: dict[str, object] = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "database": "lightrag",
        "workspace": "default",
        "max_connections": 4,
        "connection_retry_attempts": 1,
        "connection_retry_backoff": 0.1,
        "connection_retry_backoff_max": 0.1,
        "pool_close_timeout": 1.0,
    }
    config.update(overrides)
    return config


def test_default_storage_stack_points_to_the_production_backends():
    assert DefaultRAGStorageConfig.KV_STORAGE == "PGKVStorage"
    assert DefaultRAGStorageConfig.DOC_STATUS_STORAGE == "PGDocStatusStorage"
    assert DefaultRAGStorageConfig.VECTOR_STORAGE == "ChromaVectorDBStorage"
    assert DefaultRAGStorageConfig.GRAPH_STORAGE == "Neo4JStorage"

    assert LightRAG.__dataclass_fields__["kv_storage"].default == "PGKVStorage"
    assert (
        LightRAG.__dataclass_fields__["doc_status_storage"].default
        == "PGDocStatusStorage"
    )
    assert (
        LightRAG.__dataclass_fields__["vector_storage"].default
        == "ChromaVectorDBStorage"
    )
    assert LightRAG.__dataclass_fields__["graph_storage"].default == "Neo4JStorage"


def test_storage_registry_only_accepts_the_official_runtime_stack():
    assert STORAGE_IMPLEMENTATIONS["KV_STORAGE"]["implementations"] == ["PGKVStorage"]
    assert STORAGE_IMPLEMENTATIONS["DOC_STATUS_STORAGE"]["implementations"] == [
        "PGDocStatusStorage"
    ]
    assert STORAGE_IMPLEMENTATIONS["VECTOR_STORAGE"]["implementations"] == [
        "ChromaVectorDBStorage"
    ]
    assert STORAGE_IMPLEMENTATIONS["GRAPH_STORAGE"]["implementations"] == [
        "Neo4JStorage"
    ]
    assert set(STORAGES) == {
        "PGKVStorage",
        "PGDocStatusStorage",
        "ChromaVectorDBStorage",
        "Neo4JStorage",
    }

    verify_storage_implementation("KV_STORAGE", "PGKVStorage")
    verify_storage_implementation("DOC_STATUS_STORAGE", "PGDocStatusStorage")
    verify_storage_implementation("VECTOR_STORAGE", "ChromaVectorDBStorage")
    verify_storage_implementation("GRAPH_STORAGE", "Neo4JStorage")

    with pytest.raises(ValueError):
        verify_storage_implementation("KV_STORAGE", "JsonKVStorage")

    with pytest.raises(ValueError):
        verify_storage_implementation("VECTOR_STORAGE", "PGVectorStorage")

    with pytest.raises(ValueError):
        verify_storage_implementation("GRAPH_STORAGE", "NetworkXStorage")


def test_postgres_only_manages_pgvector_tables_when_pgvector_is_selected():
    chroma_db = PostgreSQLDB(_postgres_config(vector_storage="ChromaVectorDBStorage"))
    chroma_tables = set(chroma_db._managed_tables())

    assert "LIGHTRAG_VDB_CHUNKS" not in chroma_tables
    assert "LIGHTRAG_VDB_ENTITY" not in chroma_tables
    assert "LIGHTRAG_VDB_RELATION" not in chroma_tables
    assert not chroma_db.use_pgvector_backend

    pgvector_db = PostgreSQLDB(_postgres_config(vector_storage="PGVectorStorage"))
    pgvector_tables = set(pgvector_db._managed_tables())

    assert {
        "LIGHTRAG_VDB_CHUNKS",
        "LIGHTRAG_VDB_ENTITY",
        "LIGHTRAG_VDB_RELATION",
    }.issubset(pgvector_tables)
    assert pgvector_db.use_pgvector_backend
