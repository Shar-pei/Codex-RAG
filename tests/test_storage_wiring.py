from __future__ import annotations

from dataclasses import dataclass

import pytest

from lightrag.namespace import NameSpace
from lightrag.storage_wiring import (
    StorageBundle,
    StorageFactories,
    build_storage_bundle,
    build_storage_factories,
)


@dataclass
class FakeStorage:
    namespace: str
    workspace: str
    global_config: dict | None = None
    embedding_func: object | None = None
    meta_fields: set[str] | None = None

    async def initialize(self) -> None:
        return None

    async def finalize(self) -> None:
        return None

    async def index_done_callback(self) -> None:
        return None

    async def drop(self) -> dict[str, str]:
        return {"status": "success", "message": "data dropped"}


class RecordingFactory:
    def __init__(self, label: str):
        self.label = label
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return FakeStorage(**kwargs)


@pytest.mark.offline
def test_build_storage_factories_bind_global_config(monkeypatch):
    created_instances: list[FakeStorage] = []

    def fake_resolve(storage_name: str):
        def factory(**kwargs):
            instance = FakeStorage(**kwargs)
            instance.storage_name = storage_name
            created_instances.append(instance)
            return instance

        return factory

    monkeypatch.setattr("lightrag.storage_wiring.resolve_storage_class", fake_resolve)

    global_config = {"working_dir": "test-dir"}
    factories = build_storage_factories(
        kv_storage="kv",
        vector_storage="vector",
        graph_storage="graph",
        doc_status_storage="doc",
        global_config=global_config,
    )

    factories.key_value(namespace="kv-ns", workspace="ws", embedding_func="embed")
    factories.vector(namespace="vec-ns", workspace="ws", embedding_func="embed")
    factories.graph(namespace="graph-ns", workspace="ws", embedding_func="embed")
    factories.doc_status(namespace="doc-ns", workspace="ws", embedding_func=None)

    assert [instance.storage_name for instance in created_instances] == [
        "kv",
        "vector",
        "graph",
        "doc",
    ]
    assert all(instance.global_config is global_config for instance in created_instances)


@pytest.mark.offline
def test_build_storage_bundle_assigns_expected_namespaces_and_metadata():
    kv_factory = RecordingFactory("kv")
    vector_factory = RecordingFactory("vector")
    graph_factory = RecordingFactory("graph")
    doc_status_factory = RecordingFactory("doc")
    factories = StorageFactories(
        key_value=kv_factory,
        vector=vector_factory,
        graph=graph_factory,
        doc_status=doc_status_factory,
    )

    bundle = build_storage_bundle(
        factories=factories,
        workspace="workspace-a",
        embedding_func="embedding-func",
    )

    assert bundle.llm_response_cache.namespace == NameSpace.KV_STORE_LLM_RESPONSE_CACHE
    assert bundle.full_docs.namespace == NameSpace.KV_STORE_FULL_DOCS
    assert bundle.relation_chunks.namespace == NameSpace.KV_STORE_RELATION_CHUNKS
    assert (
        bundle.chunk_entity_relation_graph.namespace
        == NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION
    )
    assert bundle.entities_vdb.meta_fields == {
        "entity_name",
        "source_id",
        "content",
        "file_path",
    }
    assert bundle.relationships_vdb.meta_fields == {
        "src_id",
        "tgt_id",
        "source_id",
        "content",
        "file_path",
    }
    assert bundle.chunks_vdb.meta_fields == {"full_doc_id", "content", "file_path"}
    assert doc_status_factory.calls[0]["embedding_func"] is None
    assert all(call["workspace"] == "workspace-a" for call in kv_factory.calls)


@pytest.mark.offline
def test_storage_bundle_orders_match_lightrag_lifecycle():
    bundle = StorageBundle(
        llm_response_cache="llm_response_cache",
        text_chunks="text_chunks",
        full_docs="full_docs",
        full_entities="full_entities",
        full_relations="full_relations",
        entity_chunks="entity_chunks",
        relation_chunks="relation_chunks",
        chunk_entity_relation_graph="chunk_entity_relation_graph",
        entities_vdb="entities_vdb",
        relationships_vdb="relationships_vdb",
        chunks_vdb="chunks_vdb",
        doc_status="doc_status",
    )

    assert bundle.initialize_order() == (
        "full_docs",
        "text_chunks",
        "full_entities",
        "full_relations",
        "entity_chunks",
        "relation_chunks",
        "entities_vdb",
        "relationships_vdb",
        "chunks_vdb",
        "chunk_entity_relation_graph",
        "llm_response_cache",
        "doc_status",
    )
    assert bundle.named_storages() == (
        ("full_docs", "full_docs"),
        ("text_chunks", "text_chunks"),
        ("full_entities", "full_entities"),
        ("full_relations", "full_relations"),
        ("entity_chunks", "entity_chunks"),
        ("relation_chunks", "relation_chunks"),
        ("entities_vdb", "entities_vdb"),
        ("relationships_vdb", "relationships_vdb"),
        ("chunks_vdb", "chunks_vdb"),
        ("chunk_entity_relation_graph", "chunk_entity_relation_graph"),
        ("llm_response_cache", "llm_response_cache"),
        ("doc_status", "doc_status"),
    )
