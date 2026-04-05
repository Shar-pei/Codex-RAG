from __future__ import annotations


KNOWLEDGE_GRAPH_ROUTE_DESCRIPTION = """
Retrieve a connected subgraph of nodes where the label includes the specified label.
When reducing the number of nodes, the prioritization criteria are as follows:
    1. Hops(path) to the staring node take precedence
    2. Followed by the degree of the nodes

Args:
    label (str): Label of the starting node
    max_depth (int, optional): Maximum depth of the subgraph,Defaults to 3
    max_nodes: Maxiumu nodes to return

Returns:
    Dict[str, List[str]]: Knowledge graph for label
""".strip()


ENTITY_EDIT_ROUTE_DESCRIPTION = """
Update an entity's properties in the knowledge graph

This endpoint allows updating entity properties, including renaming entities.
When renaming to an existing entity name, the behavior depends on allow_merge:

Args:
    request (EntityUpdateRequest): Request containing:
        - entity_name (str): Name of the entity to update
        - updated_data (Dict[str, Any]): Dictionary of properties to update
        - allow_rename (bool): Whether to allow entity renaming (default: False)
        - allow_merge (bool): Whether to merge into existing entity when renaming
                             causes name conflict (default: False)

Returns:
    Dict with the following structure:
    {
        "status": "success",
        "message": "Entity updated successfully" | "Entity merged successfully into 'target_name'",
        "data": {
            "entity_name": str,        # Final entity name
            "description": str,        # Entity description
            "entity_type": str,        # Entity type
            "source_id": str,         # Source chunk IDs
            ...                       # Other entity properties
        },
        "operation_summary": {
            "merged": bool,           # Whether entity was merged into another
            "merge_status": str,      # "success" | "failed" | "not_attempted"
            "merge_error": str | None, # Error message if merge failed
            "operation_status": str,  # "success" | "partial_success" | "failure"
            "target_entity": str | None, # Target entity name if renaming/merging
            "final_entity": str,      # Final entity name after operation
            "renamed": bool           # Whether entity was renamed
        }
    }

operation_status values explained:
    - "success": All operations completed successfully
        * For simple updates: entity properties updated
        * For renames: entity renamed successfully
        * For merges: non-name updates applied AND merge completed

    - "partial_success": Update succeeded but merge failed
        * Non-name property updates were applied successfully
        * Merge operation failed (entity not merged)
        * Original entity still exists with updated properties
        * Use merge_error for failure details

    - "failure": Operation failed completely
        * If merge_status == "failed": Merge attempted but both update and merge failed
        * If merge_status == "not_attempted": Regular update failed
        * No changes were applied to the entity

merge_status values explained:
    - "success": Entity successfully merged into target entity
    - "failed": Merge operation was attempted but failed
    - "not_attempted": No merge was attempted (normal update/rename)

Behavior when renaming to an existing entity:
    - If allow_merge=False: Raises ValueError with 400 status (default behavior)
    - If allow_merge=True: Automatically merges the source entity into the existing target entity,
                          preserving all relationships and applying non-name updates first

Example Request (simple update):
    POST /graph/entity/edit
    {
        "entity_name": "Tesla",
        "updated_data": {"description": "Updated description"},
        "allow_rename": false,
        "allow_merge": false
    }

Example Response (simple update success):
    {
        "status": "success",
        "message": "Entity updated successfully",
        "data": { ... },
        "operation_summary": {
            "merged": false,
            "merge_status": "not_attempted",
            "merge_error": null,
            "operation_status": "success",
            "target_entity": null,
            "final_entity": "Tesla",
            "renamed": false
        }
    }

Example Request (rename with auto-merge):
    POST /graph/entity/edit
    {
        "entity_name": "Elon Msk",
        "updated_data": {
            "entity_name": "Elon Musk",
            "description": "Corrected description"
        },
        "allow_rename": true,
        "allow_merge": true
    }

Example Response (merge success):
    {
        "status": "success",
        "message": "Entity merged successfully into 'Elon Musk'",
        "data": { ... },
        "operation_summary": {
            "merged": true,
            "merge_status": "success",
            "merge_error": null,
            "operation_status": "success",
            "target_entity": "Elon Musk",
            "final_entity": "Elon Musk",
            "renamed": true
        }
    }

Example Response (partial success - update succeeded but merge failed):
    {
        "status": "success",
        "message": "Entity updated successfully",
        "data": { ... },  # Data reflects updated "Elon Msk" entity
        "operation_summary": {
            "merged": false,
            "merge_status": "failed",
            "merge_error": "Target entity locked by another operation",
            "operation_status": "partial_success",
            "target_entity": "Elon Musk",
            "final_entity": "Elon Msk",  # Original entity still exists
            "renamed": true
        }
    }
""".strip()


ENTITY_CREATE_ROUTE_DESCRIPTION = """
Create a new entity in the knowledge graph

This endpoint creates a new entity node in the knowledge graph with the specified
properties. The system automatically generates vector embeddings for the entity
to enable semantic search and retrieval.

Request Body:
    entity_name (str): Unique name identifier for the entity
    entity_data (dict): Entity properties including:
        - description (str): Textual description of the entity
        - entity_type (str): Category/type of the entity (e.g., PERSON, ORGANIZATION, LOCATION)
        - source_id (str): Related chunk_id from which the description originates
        - Additional custom properties as needed

Response Schema:
    {
        "status": "success",
        "message": "Entity 'Tesla' created successfully",
        "data": {
            "entity_name": "Tesla",
            "description": "Electric vehicle manufacturer",
            "entity_type": "ORGANIZATION",
            "source_id": "chunk-123<SEP>chunk-456"
            ... (other entity properties)
        }
    }

HTTP Status Codes:
    200: Entity created successfully
    400: Invalid request (e.g., missing required fields, duplicate entity)
    500: Internal server error

Example Request:
    POST /graph/entity/create
    {
        "entity_name": "Tesla",
        "entity_data": {
            "description": "Electric vehicle manufacturer",
            "entity_type": "ORGANIZATION"
        }
    }
""".strip()


RELATION_CREATE_ROUTE_DESCRIPTION = """
Create a new relationship between two entities in the knowledge graph

This endpoint establishes an undirected relationship between two existing entities.
The provided source/target order is accepted for convenience, but the backend
stored edge is undirected and may be returned with the entities swapped.
Both entities must already exist in the knowledge graph. The system automatically
generates vector embeddings for the relationship to enable semantic search and graph traversal.

Prerequisites:
    - Both source_entity and target_entity must exist in the knowledge graph
    - Use /graph/entity/create to create entities first if they don't exist

Request Body:
    source_entity (str): Name of the source entity (relationship origin)
    target_entity (str): Name of the target entity (relationship destination)
    relation_data (dict): Relationship properties including:
        - description (str): Textual description of the relationship
        - keywords (str): Comma-separated keywords describing the relationship type
        - source_id (str): Related chunk_id from which the description originates
        - weight (float): Relationship strength/importance (default: 1.0)
        - Additional custom properties as needed

Response Schema:
    {
        "status": "success",
        "message": "Relation created successfully between 'Elon Musk' and 'Tesla'",
        "data": {
            "src_id": "Elon Musk",
            "tgt_id": "Tesla",
            "description": "Elon Musk is the CEO of Tesla",
            "keywords": "CEO, founder",
            "source_id": "chunk-123<SEP>chunk-456"
            "weight": 1.0,
            ... (other relationship properties)
        }
    }

HTTP Status Codes:
    200: Relationship created successfully
    400: Invalid request (e.g., missing entities, invalid data, duplicate relationship)
    500: Internal server error

Example Request:
    POST /graph/relation/create
    {
        "source_entity": "Elon Musk",
        "target_entity": "Tesla",
        "relation_data": {
            "description": "Elon Musk is the CEO of Tesla",
            "keywords": "CEO, founder",
            "weight": 1.0
        }
    }
""".strip()


ENTITY_MERGE_ROUTE_DESCRIPTION = """
Merge multiple entities into a single entity, preserving all relationships

This endpoint consolidates duplicate or misspelled entities while preserving the entire
graph structure. It's particularly useful for cleaning up knowledge graphs after document
processing or correcting entity name variations.

What the Merge Operation Does:
    1. Deletes the specified source entities from the knowledge graph
    2. Transfers all relationships from source entities to the target entity
    3. Intelligently merges duplicate relationships (if multiple sources have the same relationship)
    4. Updates vector embeddings for accurate retrieval and search
    5. Preserves the complete graph structure and connectivity
    6. Maintains relationship properties and metadata

Use Cases:
    - Fixing spelling errors in entity names (e.g., "Elon Msk" -> "Elon Musk")
    - Consolidating duplicate entities discovered after document processing
    - Merging name variations (e.g., "NY", "New York", "New York City")
    - Cleaning up the knowledge graph for better query performance
    - Standardizing entity names across the knowledge base

Request Body:
    entities_to_change (list[str]): List of entity names to be merged and deleted
    entity_to_change_into (str): Target entity that will receive all relationships

Response Schema:
    {
        "status": "success",
        "message": "Successfully merged 2 entities into 'Elon Musk'",
        "data": {
            "merged_entity": "Elon Musk",
            "deleted_entities": ["Elon Msk", "Ellon Musk"],
            "relationships_transferred": 15,
            ... (merge operation details)
        }
    }

HTTP Status Codes:
    200: Entities merged successfully
    400: Invalid request (e.g., empty entity list, target entity doesn't exist)
    500: Internal server error

Example Request:
    POST /graph/entities/merge
    {
        "entities_to_change": ["Elon Msk", "Ellon Musk"],
        "entity_to_change_into": "Elon Musk"
    }

Note:
    - The target entity (entity_to_change_into) must exist in the knowledge graph
    - Source entities will be permanently deleted after the merge
    - This operation cannot be undone, so verify entity names before merging
""".strip()
