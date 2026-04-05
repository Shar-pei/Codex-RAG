from __future__ import annotations

import traceback

from fastapi import HTTPException

from lightrag.utils import logger


async def update_entity_response(rag, request):
    try:
        result = await rag.aedit_entity(
            entity_name=request.entity_name,
            updated_data=request.updated_data,
            allow_rename=request.allow_rename,
            allow_merge=request.allow_merge,
        )

        operation_summary = result.get(
            "operation_summary",
            {
                "merged": False,
                "merge_status": "not_attempted",
                "merge_error": None,
                "operation_status": "success",
                "target_entity": None,
                "final_entity": request.updated_data.get(
                    "entity_name", request.entity_name
                ),
                "renamed": request.updated_data.get("entity_name", request.entity_name)
                != request.entity_name,
            },
        )

        entity_data = dict(result)
        entity_data.pop("operation_summary", None)

        response_message = (
            f"Entity merged successfully into '{operation_summary['final_entity']}'"
            if operation_summary.get("merged")
            else "Entity updated successfully"
        )
        return {
            "status": "success",
            "message": response_message,
            "data": entity_data,
            "operation_summary": operation_summary,
        }
    except ValueError as ve:
        logger.error(f"Validation error updating entity '{request.entity_name}': {ve}")
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(f"Error updating entity '{request.entity_name}': {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating entity: {e}"
        ) from e


async def update_relation_response(rag, request):
    try:
        result = await rag.aedit_relation(
            source_entity=request.source_id,
            target_entity=request.target_id,
            updated_data=request.updated_data,
        )
        return {
            "status": "success",
            "message": "Relation updated successfully",
            "data": result,
        }
    except ValueError as ve:
        logger.error(
            f"Validation error updating relation between '{request.source_id}' and '{request.target_id}': {ve}"
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(
            f"Error updating relation between '{request.source_id}' and '{request.target_id}': {e}"
        )
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating relation: {e}"
        ) from e


async def create_entity_response(rag, request):
    try:
        result = await rag.acreate_entity(
            entity_name=request.entity_name,
            entity_data=request.entity_data,
        )

        return {
            "status": "success",
            "message": f"Entity '{request.entity_name}' created successfully",
            "data": result,
        }
    except ValueError as ve:
        logger.error(f"Validation error creating entity '{request.entity_name}': {ve}")
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(f"Error creating entity '{request.entity_name}': {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error creating entity: {e}"
        ) from e


async def create_relation_response(rag, request):
    try:
        result = await rag.acreate_relation(
            source_entity=request.source_entity,
            target_entity=request.target_entity,
            relation_data=request.relation_data,
        )

        return {
            "status": "success",
            "message": f"Relation created successfully between '{request.source_entity}' and '{request.target_entity}'",
            "data": result,
        }
    except ValueError as ve:
        logger.error(
            f"Validation error creating relation between '{request.source_entity}' and '{request.target_entity}': {ve}"
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(
            f"Error creating relation between '{request.source_entity}' and '{request.target_entity}': {e}"
        )
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error creating relation: {e}"
        ) from e


async def merge_entities_response(rag, request):
    try:
        result = await rag.amerge_entities(
            source_entities=request.entities_to_change,
            target_entity=request.entity_to_change_into,
        )
        return {
            "status": "success",
            "message": f"Successfully merged {len(request.entities_to_change)} entities into '{request.entity_to_change_into}'",
            "data": result,
        }
    except ValueError as ve:
        logger.error(
            f"Validation error merging entities {request.entities_to_change} into '{request.entity_to_change_into}': {ve}"
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        logger.error(
            f"Error merging entities {request.entities_to_change} into '{request.entity_to_change_into}': {e}"
        )
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error merging entities: {e}"
        ) from e
