#!/usr/bin/env python3
"""Migrate legacy local LightRAG storage into Postgres + Chroma + Neo4j."""

from __future__ import annotations

import argparse
import asyncio
import base64
import os
import sys
import zlib
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lightrag.kg.chroma_impl import ChromaVectorDBStorage
from lightrag.kg.neo4j_impl import Neo4JStorage
from lightrag.kg.networkx_impl import NetworkXStorage
from lightrag.kg.postgres_impl import (
    PGDocStatusStorage,
    PGKVStorage,
    namespace_to_table_name,
)
from lightrag.kg.shared_storage import initialize_share_data
from lightrag.namespace import NameSpace
from lightrag.utils import EmbeddingFunc, load_json, logger, setup_logger

load_dotenv(dotenv_path=".env", override=False)
setup_logger("lightrag", level=os.getenv("LOG_LEVEL", "INFO"))


KV_NAMESPACE_FILES = {
    NameSpace.KV_STORE_FULL_DOCS: "kv_store_full_docs.json",
    NameSpace.KV_STORE_TEXT_CHUNKS: "kv_store_text_chunks.json",
    NameSpace.KV_STORE_LLM_RESPONSE_CACHE: "kv_store_llm_response_cache.json",
    NameSpace.KV_STORE_FULL_ENTITIES: "kv_store_full_entities.json",
    NameSpace.KV_STORE_FULL_RELATIONS: "kv_store_full_relations.json",
    NameSpace.KV_STORE_ENTITY_CHUNKS: "kv_store_entity_chunks.json",
    NameSpace.KV_STORE_RELATION_CHUNKS: "kv_store_relation_chunks.json",
}

VECTOR_NAMESPACE_FILES = {
    NameSpace.VECTOR_STORE_ENTITIES: "vdb_entities.json",
    NameSpace.VECTOR_STORE_RELATIONSHIPS: "vdb_relationships.json",
    NameSpace.VECTOR_STORE_CHUNKS: "vdb_chunks.json",
}

DOC_STATUS_FILE = "kv_store_doc_status.json"
GRAPH_FILE = f"graph_{NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION}.graphml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate legacy local LightRAG storage "
            "(JSON + NanoVectorDB + NetworkX) to Postgres + Chroma + Neo4j."
        )
    )
    parser.add_argument(
        "--working-dir",
        default="rag_storage",
        help="Legacy local storage directory. Defaults to ./rag_storage",
    )
    parser.add_argument(
        "--workspace",
        default="",
        help="Workspace name used by the legacy local storage. Empty means the root working dir.",
    )
    parser.add_argument(
        "--drop-target",
        action="store_true",
        help="Drop target workspace data before migration.",
    )
    parser.add_argument(
        "--skip-if-target-exists",
        action="store_true",
        help="Exit successfully without migrating when target data already exists.",
    )
    return parser.parse_args()


def get_source_dir(working_dir: Path, workspace: str) -> Path:
    return working_dir / workspace if workspace else working_dir


def require_json_file(path: Path) -> dict[str, Any]:
    data = load_json(str(path))
    if data is None:
        raise FileNotFoundError(f"Missing source file: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def load_kv_payloads(source_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for namespace, file_name in KV_NAMESPACE_FILES.items():
        payloads[namespace] = require_json_file(source_dir / file_name)
    return payloads


def load_doc_status_payload(source_dir: Path) -> dict[str, dict[str, Any]]:
    return require_json_file(source_dir / DOC_STATUS_FILE)


def decode_legacy_vector(encoded_vector: str) -> list[float]:
    decoded = base64.b64decode(encoded_vector)
    decompressed = zlib.decompress(decoded)
    vector_f16 = np.frombuffer(decompressed, dtype=np.float16)
    return vector_f16.astype(np.float32).tolist()


def load_vector_payloads(
    source_dir: Path,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, int]]:
    payloads: dict[str, dict[str, dict[str, Any]]] = {}
    dimensions: dict[str, int] = {}

    for namespace, file_name in VECTOR_NAMESPACE_FILES.items():
        raw = require_json_file(source_dir / file_name)
        dim = int(raw.get("embedding_dim", 0))
        if dim <= 0:
            raise ValueError(f"Missing embedding_dim in {source_dir / file_name}")

        records: dict[str, dict[str, Any]] = {}
        for item in raw.get("data", []):
            item_id = item.get("__id__")
            encoded_vector = item.get("vector")
            if not item_id or not encoded_vector:
                raise ValueError(f"Malformed vector record in {source_dir / file_name}")

            migrated = {
                key: value
                for key, value in item.items()
                if key not in {"__id__", "__vector__", "vector"}
            }
            migrated["created_at"] = item.get("__created_at__")
            migrated["vector"] = decode_legacy_vector(encoded_vector)
            records[str(item_id)] = migrated

        payloads[namespace] = records
        dimensions[namespace] = dim

    return payloads, dimensions


def load_graph_payload(source_dir: Path):
    graph_path = source_dir / GRAPH_FILE
    graph = NetworkXStorage.load_nx_graph(str(graph_path))
    if graph is None:
        raise FileNotFoundError(f"Missing source graph file: {graph_path}")
    return graph


async def unused_embedding(_: list[str], **__: Any) -> np.ndarray:
    raise RuntimeError(
        "Migration should not compute embeddings. Legacy vectors must be provided explicitly."
    )


def build_global_config(working_dir: Path) -> dict[str, Any]:
    return {
        "working_dir": str(working_dir),
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {
            "cosine_better_than_threshold": 0.2,
        },
    }


def build_embedding_func(embedding_dim: int) -> EmbeddingFunc:
    return EmbeddingFunc(embedding_dim=embedding_dim, func=unused_embedding)


def vector_meta_fields(namespace: str) -> set[str]:
    if namespace == NameSpace.VECTOR_STORE_ENTITIES:
        return {"entity_name", "source_id", "content", "file_path"}
    if namespace == NameSpace.VECTOR_STORE_RELATIONSHIPS:
        return {"src_id", "tgt_id", "source_id", "content", "file_path"}
    if namespace == NameSpace.VECTOR_STORE_CHUNKS:
        return {"full_doc_id", "content", "file_path"}
    raise ValueError(f"Unsupported vector namespace: {namespace}")


async def postgres_count(storage: PGKVStorage | PGDocStatusStorage) -> int:
    table_name = namespace_to_table_name(storage.namespace)
    if not table_name:
        raise ValueError(f"Unknown PostgreSQL namespace: {storage.namespace}")
    row = await storage.db.query(
        f"SELECT COUNT(*) AS count FROM {table_name} WHERE workspace=$1",
        [storage.workspace],
    )
    return int(row["count"]) if row else 0


async def chroma_count(storage: ChromaVectorDBStorage) -> int:
    return int(storage._ensure_collection().count())


async def neo4j_counts(storage: Neo4JStorage) -> tuple[int, int]:
    workspace_label = storage._get_workspace_label()
    async with storage._driver.session(database=storage._DATABASE) as session:
        node_result = await session.run(
            f"MATCH (n:`{workspace_label}`) RETURN count(n) AS count"
        )
        node_record = await node_result.single()
        edge_result = await session.run(
            f"MATCH (n:`{workspace_label}`)-[r]-() RETURN count(DISTINCT r) AS count"
        )
        edge_record = await edge_result.single()
    return (
        int(node_record["count"]) if node_record else 0,
        int(edge_record["count"]) if edge_record else 0,
    )


async def ensure_target_is_empty(
    kv_storages: dict[str, PGKVStorage],
    doc_status_storage: PGDocStatusStorage,
    vector_storages: dict[str, ChromaVectorDBStorage],
    graph_storage: Neo4JStorage,
    skip_if_target_exists: bool,
) -> bool:
    target_counts: dict[str, int] = {}

    for namespace, storage in kv_storages.items():
        target_counts[namespace] = await postgres_count(storage)
    target_counts[NameSpace.DOC_STATUS] = await postgres_count(doc_status_storage)
    for namespace, storage in vector_storages.items():
        target_counts[namespace] = await chroma_count(storage)

    node_count, edge_count = await neo4j_counts(graph_storage)
    target_counts["neo4j_nodes"] = node_count
    target_counts["neo4j_edges"] = edge_count

    has_existing_data = any(count > 0 for count in target_counts.values())
    if not has_existing_data:
        return False

    summary = ", ".join(f"{name}={count}" for name, count in target_counts.items())
    if skip_if_target_exists:
        logger.warning("Target data already exists, skipping migration: %s", summary)
        return True

    raise RuntimeError(
        "Target workspace already contains data. "
        "Use --drop-target to overwrite or --skip-if-target-exists to skip. "
        f"Current counts: {summary}"
    )


async def migrate_graph(graph_storage: Neo4JStorage, source_graph) -> None:
    for node_id, node_data in source_graph.nodes(data=True):
        payload = dict(node_data)
        payload.setdefault("entity_id", node_id)
        payload.setdefault("entity_type", "UNKNOWN")
        await graph_storage.upsert_node(str(node_id), payload)

    for source_id, target_id, edge_data in source_graph.edges(data=True):
        await graph_storage.upsert_edge(str(source_id), str(target_id), dict(edge_data))


async def print_summary(
    kv_storages: dict[str, PGKVStorage],
    doc_status_storage: PGDocStatusStorage,
    vector_storages: dict[str, ChromaVectorDBStorage],
    graph_storage: Neo4JStorage,
) -> None:
    print("Migration completed.")
    print("Postgres counts:")
    for namespace, storage in kv_storages.items():
        print(f"  {namespace}: {await postgres_count(storage)}")
    print(
        f"  {NameSpace.DOC_STATUS}: {await postgres_count(doc_status_storage)}"
    )

    print("Chroma counts:")
    for namespace, storage in vector_storages.items():
        print(f"  {namespace}: {await chroma_count(storage)}")

    node_count, edge_count = await neo4j_counts(graph_storage)
    print("Neo4j counts:")
    print(f"  nodes: {node_count}")
    print(f"  edges: {edge_count}")


async def async_main(args: argparse.Namespace) -> int:
    initialize_share_data()

    working_dir = Path(args.working_dir).expanduser().resolve()
    source_dir = get_source_dir(working_dir, args.workspace)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source working directory does not exist: {source_dir}")

    kv_payloads = load_kv_payloads(source_dir)
    doc_status_payload = load_doc_status_payload(source_dir)
    vector_payloads, vector_dimensions = load_vector_payloads(source_dir)
    source_graph = load_graph_payload(source_dir)

    global_config = build_global_config(working_dir)
    kv_embedding = build_embedding_func(1)

    kv_storages: dict[str, PGKVStorage] = {
        namespace: PGKVStorage(
            namespace=namespace,
            workspace=args.workspace,
            global_config=global_config,
            embedding_func=kv_embedding,
        )
        for namespace in KV_NAMESPACE_FILES
    }
    doc_status_storage = PGDocStatusStorage(
        namespace=NameSpace.DOC_STATUS,
        workspace=args.workspace,
        global_config=global_config,
        embedding_func=kv_embedding,
    )
    vector_storages: dict[str, ChromaVectorDBStorage] = {
        namespace: ChromaVectorDBStorage(
            namespace=namespace,
            workspace=args.workspace,
            global_config=global_config,
            embedding_func=build_embedding_func(vector_dimensions[namespace]),
            meta_fields=vector_meta_fields(namespace),
        )
        for namespace in VECTOR_NAMESPACE_FILES
    }
    graph_storage = Neo4JStorage(
        namespace=NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION,
        workspace=args.workspace,
        global_config=global_config,
        embedding_func=kv_embedding,
    )

    storages = [
        *kv_storages.values(),
        doc_status_storage,
        *vector_storages.values(),
        graph_storage,
    ]

    try:
        await asyncio.gather(*(storage.initialize() for storage in storages))

        if args.drop_target:
            await asyncio.gather(
                *(storage.drop() for storage in kv_storages.values()),
                doc_status_storage.drop(),
                *(storage.drop() for storage in vector_storages.values()),
                graph_storage.drop(),
            )
        else:
            skipped = await ensure_target_is_empty(
                kv_storages=kv_storages,
                doc_status_storage=doc_status_storage,
                vector_storages=vector_storages,
                graph_storage=graph_storage,
                skip_if_target_exists=args.skip_if_target_exists,
            )
            if skipped:
                return 0

        for namespace, storage in kv_storages.items():
            await storage.upsert(kv_payloads[namespace])

        await doc_status_storage.upsert(doc_status_payload)

        for namespace, storage in vector_storages.items():
            await storage.upsert(vector_payloads[namespace])

        await migrate_graph(graph_storage, source_graph)

        await asyncio.gather(
            *(storage.index_done_callback() for storage in kv_storages.values()),
            doc_status_storage.index_done_callback(),
            *(storage.index_done_callback() for storage in vector_storages.values()),
            graph_storage.index_done_callback(),
        )

        await print_summary(
            kv_storages=kv_storages,
            doc_status_storage=doc_status_storage,
            vector_storages=vector_storages,
            graph_storage=graph_storage,
        )
        return 0
    finally:
        await asyncio.gather(
            *(storage.finalize() for storage in storages), return_exceptions=True
        )


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
