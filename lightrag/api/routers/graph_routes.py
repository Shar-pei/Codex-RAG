"""
This module contains all graph-related routes for the LightRAG API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from lightrag.api.routers.graph_models import (
    EntityCreateRequest as _EntityCreateRequest,
    EntityMergeRequest as _EntityMergeRequest,
    EntityUpdateRequest as _EntityUpdateRequest,
    RelationCreateRequest as _RelationCreateRequest,
    RelationUpdateRequest as _RelationUpdateRequest,
)
from lightrag.api.routers.graph_mutation_commands import (
    create_entity_response as _create_entity_response,
    create_relation_response as _create_relation_response,
    merge_entities_response as _merge_entities_response,
    update_entity_response as _update_entity_response,
    update_relation_response as _update_relation_response,
)
from lightrag.api.routers.graph_query_helpers import (
    check_entity_exists_response as _check_entity_exists_response,
    get_graph_labels_response as _get_graph_labels_response,
    get_knowledge_graph_response as _get_knowledge_graph_response,
    get_popular_labels_response as _get_popular_labels_response,
    search_labels_response as _search_labels_response,
)
from lightrag.api.routers.graph_route_descriptions import (
    ENTITY_CREATE_ROUTE_DESCRIPTION as _ENTITY_CREATE_ROUTE_DESCRIPTION,
    ENTITY_EDIT_ROUTE_DESCRIPTION as _ENTITY_EDIT_ROUTE_DESCRIPTION,
    ENTITY_MERGE_ROUTE_DESCRIPTION as _ENTITY_MERGE_ROUTE_DESCRIPTION,
    KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION as _KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION,
    RELATION_CREATE_ROUTE_DESCRIPTION as _RELATION_CREATE_ROUTE_DESCRIPTION,
)

from ..utils_api import get_combined_auth_dependency

router = APIRouter(tags=["graph"])

EntityUpdateRequest = _EntityUpdateRequest
RelationUpdateRequest = _RelationUpdateRequest
EntityMergeRequest = _EntityMergeRequest
EntityCreateRequest = _EntityCreateRequest
RelationCreateRequest = _RelationCreateRequest
KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION = _KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION
ENTITY_EDIT_ROUTE_DESCRIPTION = _ENTITY_EDIT_ROUTE_DESCRIPTION
ENTITY_CREATE_ROUTE_DESCRIPTION = _ENTITY_CREATE_ROUTE_DESCRIPTION
RELATION_CREATE_ROUTE_DESCRIPTION = _RELATION_CREATE_ROUTE_DESCRIPTION
ENTITY_MERGE_ROUTE_DESCRIPTION = _ENTITY_MERGE_ROUTE_DESCRIPTION
update_entity_response = _update_entity_response
update_relation_response = _update_relation_response
create_entity_response = _create_entity_response
create_relation_response = _create_relation_response
merge_entities_response = _merge_entities_response
get_graph_labels_response = _get_graph_labels_response
get_popular_labels_response = _get_popular_labels_response
search_labels_response = _search_labels_response
get_knowledge_graph_response = _get_knowledge_graph_response
check_entity_exists_response = _check_entity_exists_response


def create_graph_routes(rag, api_key: Optional[str] = None):
    router = APIRouter(tags=["graph"])
    combined_auth = get_combined_auth_dependency(api_key)

    @router.get("/graph/label/list", dependencies=[Depends(combined_auth)])
    async def get_graph_labels():
        return await get_graph_labels_response(rag)

    @router.get("/graph/label/popular", dependencies=[Depends(combined_auth)])
    async def get_popular_labels(
        limit: int = Query(
            300, description="Maximum number of popular labels to return", ge=1, le=1000
        ),
    ):
        """
        Get popular labels by node degree (most connected entities)

        Args:
            limit (int): Maximum number of labels to return (default: 300, max: 1000)

        Returns:
            List[str]: List of popular labels sorted by degree (highest first)
        """
        return await get_popular_labels_response(rag, limit)

    @router.get("/graph/label/search", dependencies=[Depends(combined_auth)])
    async def search_labels(
        q: str = Query(..., description="Search query string"),
        limit: int = Query(
            50, description="Maximum number of search results to return", ge=1, le=100
        ),
    ):
        """
        Search labels with fuzzy matching

        Args:
            q (str): Search query string
            limit (int): Maximum number of results to return (default: 50, max: 100)

        Returns:
            List[str]: List of matching labels sorted by relevance
        """
        return await search_labels_response(rag, q, limit)

    @router.get(
        "/graphs",
        dependencies=[Depends(combined_auth)],
        description=KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION,
    )
    async def get_knowledge_graph(
        label: str = Query(..., description="Label to get knowledge graph for"),
        max_depth: int = Query(3, description="Maximum depth of graph", ge=1),
        max_nodes: int = Query(1000, description="Maximum nodes to return", ge=1),
    ):
        return await get_knowledge_graph_response(rag, label, max_depth, max_nodes)

    @router.get("/graph/entity/exists", dependencies=[Depends(combined_auth)])
    async def check_entity_exists(
        name: str = Query(..., description="Entity name to check"),
    ):
        """
        Check if an entity with the given name exists in the knowledge graph

        Args:
            name (str): Name of the entity to check

        Returns:
            Dict[str, bool]: Dictionary with 'exists' key indicating if entity exists
        """
        return await check_entity_exists_response(rag, name)

    @router.post(
        "/graph/entity/edit",
        dependencies=[Depends(combined_auth)],
        description=ENTITY_EDIT_ROUTE_DESCRIPTION,
    )
    async def update_entity(request: EntityUpdateRequest):
        return await update_entity_response(rag, request)

    @router.post("/graph/relation/edit", dependencies=[Depends(combined_auth)])
    async def update_relation(request: RelationUpdateRequest):
        """Update a relation's properties in the knowledge graph

        Args:
            request (RelationUpdateRequest): Request containing source ID, target ID and updated data

        Returns:
            Dict: Updated relation information
        """
        return await update_relation_response(rag, request)

    @router.post(
        "/graph/entity/create",
        dependencies=[Depends(combined_auth)],
        description=ENTITY_CREATE_ROUTE_DESCRIPTION,
    )
    async def create_entity(request: EntityCreateRequest):
        return await create_entity_response(rag, request)

    @router.post(
        "/graph/relation/create",
        dependencies=[Depends(combined_auth)],
        description=RELATION_CREATE_ROUTE_DESCRIPTION,
    )
    async def create_relation(request: RelationCreateRequest):
        return await create_relation_response(rag, request)

    @router.post(
        "/graph/entities/merge",
        dependencies=[Depends(combined_auth)],
        description=ENTITY_MERGE_ROUTE_DESCRIPTION,
    )
    async def merge_entities(request: EntityMergeRequest):
        return await merge_entities_response(rag, request)

    return router
