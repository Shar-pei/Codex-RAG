from __future__ import annotations

import traceback

from fastapi import HTTPException

from lightrag.utils import logger


async def get_graph_labels_response(rag):
    try:
        return await rag.get_graph_labels()
    except Exception as e:
        logger.error(f"Error getting graph labels: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting graph labels: {e}"
        ) from e


async def get_popular_labels_response(rag, limit: int):
    try:
        return await rag.chunk_entity_relation_graph.get_popular_labels(limit)
    except Exception as e:
        logger.error(f"Error getting popular labels: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting popular labels: {e}"
        ) from e


async def search_labels_response(rag, q: str, limit: int):
    try:
        return await rag.chunk_entity_relation_graph.search_labels(q, limit)
    except Exception as e:
        logger.error(f"Error searching labels with query '{q}': {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error searching labels: {e}"
        ) from e


async def get_knowledge_graph_response(
    rag, label: str, max_depth: int, max_nodes: int
):
    try:
        logger.debug(
            f"get_knowledge_graph called with label: '{label}' (length: {len(label)}, repr: {repr(label)})"
        )

        return await rag.get_knowledge_graph(
            node_label=label,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    except Exception as e:
        logger.error(f"Error getting knowledge graph for label '{label}': {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting knowledge graph: {e}"
        ) from e


async def check_entity_exists_response(rag, name: str):
    try:
        exists = await rag.chunk_entity_relation_graph.has_node(name)
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking entity existence for '{name}': {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error checking entity existence: {e}"
        ) from e
