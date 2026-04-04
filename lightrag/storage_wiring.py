from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, cast

from lightrag.base import (
    BaseGraphStorage,
    BaseKVStorage,
    BaseVectorStorage,
    DocStatusStorage,
    StorageNameSpace,
)
from lightrag.kg import STORAGES
from lightrag.namespace import NameSpace
from lightrag.utils import lazy_external_import


@dataclass(frozen=True)
class StorageFactories:
    key_value: Callable[..., BaseKVStorage]
    vector: Callable[..., BaseVectorStorage]
    graph: Callable[..., BaseGraphStorage]
    doc_status: Callable[..., DocStatusStorage]


@dataclass
class StorageBundle:
    llm_response_cache: BaseKVStorage
    text_chunks: BaseKVStorage
    full_docs: BaseKVStorage
    full_entities: BaseKVStorage
    full_relations: BaseKVStorage
    entity_chunks: BaseKVStorage
    relation_chunks: BaseKVStorage
    chunk_entity_relation_graph: BaseGraphStorage
    entities_vdb: BaseVectorStorage
    relationships_vdb: BaseVectorStorage
    chunks_vdb: BaseVectorStorage
    doc_status: DocStatusStorage

    def initialize_order(self) -> tuple[StorageNameSpace, ...]:
        return (
            self.full_docs,
            self.text_chunks,
            self.full_entities,
            self.full_relations,
            self.entity_chunks,
            self.relation_chunks,
            self.entities_vdb,
            self.relationships_vdb,
            self.chunks_vdb,
            self.chunk_entity_relation_graph,
            self.llm_response_cache,
            self.doc_status,
        )

    def named_storages(self) -> tuple[tuple[str, StorageNameSpace], ...]:
        return (
            ("full_docs", self.full_docs),
            ("text_chunks", self.text_chunks),
            ("full_entities", self.full_entities),
            ("full_relations", self.full_relations),
            ("entity_chunks", self.entity_chunks),
            ("relation_chunks", self.relation_chunks),
            ("entities_vdb", self.entities_vdb),
            ("relationships_vdb", self.relationships_vdb),
            ("chunks_vdb", self.chunks_vdb),
            ("chunk_entity_relation_graph", self.chunk_entity_relation_graph),
            ("llm_response_cache", self.llm_response_cache),
            ("doc_status", self.doc_status),
        )


def resolve_storage_class(storage_name: str) -> Callable[..., Any]:
    if storage_name == "PGKVStorage":
        from lightrag.kg.postgres_impl import PGKVStorage

        return PGKVStorage
    if storage_name == "ChromaVectorDBStorage":
        from lightrag.kg.chroma_impl import ChromaVectorDBStorage

        return ChromaVectorDBStorage
    if storage_name == "Neo4JStorage":
        from lightrag.kg.neo4j_impl import Neo4JStorage

        return Neo4JStorage
    if storage_name == "PGDocStatusStorage":
        from lightrag.kg.postgres_impl import PGDocStatusStorage

        return PGDocStatusStorage

    import_path = STORAGES[storage_name]
    return lazy_external_import(import_path, storage_name)


def build_storage_factories(
    *,
    kv_storage: str,
    vector_storage: str,
    graph_storage: str,
    doc_status_storage: str,
    global_config: dict[str, Any],
) -> StorageFactories:
    return StorageFactories(
        key_value=cast(
            Callable[..., BaseKVStorage],
            partial(resolve_storage_class(kv_storage), global_config=global_config),
        ),
        vector=cast(
            Callable[..., BaseVectorStorage],
            partial(
                resolve_storage_class(vector_storage),
                global_config=global_config,
            ),
        ),
        graph=cast(
            Callable[..., BaseGraphStorage],
            partial(resolve_storage_class(graph_storage), global_config=global_config),
        ),
        doc_status=cast(
            Callable[..., DocStatusStorage],
            partial(
                resolve_storage_class(doc_status_storage),
                global_config=global_config,
            ),
        ),
    )


def build_storage_bundle(
    *,
    factories: StorageFactories,
    workspace: str,
    embedding_func: Any,
) -> StorageBundle:
    return StorageBundle(
        llm_response_cache=factories.key_value(
            namespace=NameSpace.KV_STORE_LLM_RESPONSE_CACHE,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        text_chunks=factories.key_value(
            namespace=NameSpace.KV_STORE_TEXT_CHUNKS,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        full_docs=factories.key_value(
            namespace=NameSpace.KV_STORE_FULL_DOCS,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        full_entities=factories.key_value(
            namespace=NameSpace.KV_STORE_FULL_ENTITIES,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        full_relations=factories.key_value(
            namespace=NameSpace.KV_STORE_FULL_RELATIONS,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        entity_chunks=factories.key_value(
            namespace=NameSpace.KV_STORE_ENTITY_CHUNKS,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        relation_chunks=factories.key_value(
            namespace=NameSpace.KV_STORE_RELATION_CHUNKS,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        chunk_entity_relation_graph=factories.graph(
            namespace=NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION,
            workspace=workspace,
            embedding_func=embedding_func,
        ),
        entities_vdb=factories.vector(
            namespace=NameSpace.VECTOR_STORE_ENTITIES,
            workspace=workspace,
            embedding_func=embedding_func,
            meta_fields={"entity_name", "source_id", "content", "file_path"},
        ),
        relationships_vdb=factories.vector(
            namespace=NameSpace.VECTOR_STORE_RELATIONSHIPS,
            workspace=workspace,
            embedding_func=embedding_func,
            meta_fields={"src_id", "tgt_id", "source_id", "content", "file_path"},
        ),
        chunks_vdb=factories.vector(
            namespace=NameSpace.VECTOR_STORE_CHUNKS,
            workspace=workspace,
            embedding_func=embedding_func,
            meta_fields={"full_doc_id", "content", "file_path"},
        ),
        doc_status=factories.doc_status(
            namespace=NameSpace.DOC_STATUS,
            workspace=workspace,
            embedding_func=None,
        ),
    )
