import lightrag.indexing as indexing
import lightrag.operate as operate
import lightrag.retrieval as retrieval
from lightrag.lightrag import LightRAG


def test_operate_reexports_indexing_and_retrieval_functions():
    assert operate.chunking_by_token_size is indexing.chunking_by_token_size
    assert (
        operate.semantic_chunking_by_token_size
        is indexing.semantic_chunking_by_token_size
    )
    assert operate.rebuild_knowledge_from_chunks is indexing.rebuild_knowledge_from_chunks
    assert operate.merge_nodes_and_edges is indexing.merge_nodes_and_edges
    assert operate.extract_entities is indexing.extract_entities
    assert operate.kg_query is retrieval.kg_query
    assert operate.naive_query is retrieval.naive_query


def test_lightrag_import_survives_operate_split():
    assert LightRAG.__name__ == "LightRAG"
