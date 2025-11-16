"""
Query API Routes
Handles unified query interface endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from app.controllers.query_controller import QueryController
from app.models.query_models import QueryRequest, QueryResponse
from app.security import get_current_user


router = APIRouter()


@router.post("/data/query", response_model=QueryResponse)
async def query_data(
    request: QueryRequest,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Query data from any entity (table or collection)
    
    - Unified interface for SQL and NoSQL
    - MongoDB-style query syntax
    - Supports filters, sort, pagination, projection
    - Automatically translates to SQL or MongoDB queries
    
    Example:
    ```json
    {
      "entity": "users",
      "filters": {"age": {"$gt": 25}},
      "sort": {"name": 1},
      "limit": 50,
      "offset": 0,
      "fields": ["id", "name", "email"]
    }
    ```
    """
    result = await QueryController.query_data(
        entity=request.entity,
        filters=request.filters,
        sort=request.sort,
        limit=request.limit,
        offset=request.offset,
        fields=request.fields
    )
    
    return result
