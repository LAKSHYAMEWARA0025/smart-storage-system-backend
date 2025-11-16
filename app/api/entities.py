"""
Entities API Routes
Handles entity management endpoints
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID

from app.controllers.entities_controller import EntitiesController
from app.models.query_models import (
    EntitiesListResponse,
    EntitySchemaResponse,
    EntityStatsResponse
)
from app.security import get_current_user


router = APIRouter()


@router.get("/data/entities", response_model=EntitiesListResponse)
async def list_entities(
    storage_type: Optional[str] = Query(None, description="Filter by storage type: 'sql' or 'nosql'"),
    current_user_id: UUID = Depends(get_current_user)
):
    """
    List all entities (tables and collections)
    
    - Returns all entities accessible to the user
    - Can filter by storage type
    - Includes metadata like record count, creation date, etc.
    
    Example:
    ```
    GET /api/data/entities
    GET /api/data/entities?storage_type=sql
    ```
    """
    result = await EntitiesController.list_entities(
        storage_type=storage_type,
        user_id=str(current_user_id)
    )
    
    return result


@router.get("/data/entities/{entity_name}/schema", response_model=EntitySchemaResponse)
async def get_entity_schema(
    entity_name: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get schema details for a specific entity
    
    - Returns complete schema definition
    - Includes field types, nullable flags, indexes
    - Shows core vs optional fields
    
    Example:
    ```
    GET /api/data/entities/users/schema
    ```
    """
    result = await EntitiesController.get_entity_schema(entity_name)
    
    return result


@router.get("/data/entities/{entity_name}/stats", response_model=EntityStatsResponse)
async def get_entity_stats(
    entity_name: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get statistics for a specific entity
    
    - Returns record count, storage size, indexes
    - Includes creation and update timestamps
    - Shows storage type and location
    
    Example:
    ```
    GET /api/data/entities/users/stats
    ```
    """
    result = await EntitiesController.get_entity_stats(entity_name)
    
    return result


@router.get("/data/registry/stats")
async def get_registry_stats(
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get overall registry statistics
    
    - Total number of schemas
    - SQL vs NoSQL breakdown
    - Total records across all entities
    - Average records per schema
    
    Example:
    ```
    GET /api/data/registry/stats
    ```
    """
    result = await EntitiesController.get_registry_statistics()
    
    return result
