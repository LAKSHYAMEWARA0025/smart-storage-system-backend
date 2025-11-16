"""
Pydantic Models for Query API
Request and response models for unified query interface
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================================
# QUERY REQUEST MODELS
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for unified query endpoint"""
    entity: str = Field(..., description="Entity name (table/collection)")
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="MongoDB-style query filters"
    )
    sort: Optional[Dict[str, int]] = Field(
        default_factory=dict,
        description="Sort specification: {field: 1 (asc) or -1 (desc)}"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip"
    )
    fields: Optional[List[str]] = Field(
        None,
        description="Fields to include in response (projection)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity": "users",
                "filters": {
                    "age": {"$gt": 25},
                    "status": "active"
                },
                "sort": {"created_at": -1},
                "limit": 50,
                "offset": 0,
                "fields": ["id", "name", "email"]
            }
        }


# ============================================================================
# QUERY RESPONSE MODELS
# ============================================================================

class PaginationInfo(BaseModel):
    """Pagination information"""
    limit: int = Field(..., description="Records per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more records exist")
    total_count: Optional[int] = Field(None, description="Total count (if available)")


class QueryResponse(BaseModel):
    """Response from query endpoint"""
    entity: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type: 'sql' or 'nosql'")
    returned_count: int = Field(..., description="Number of records returned")
    data: List[Dict[str, Any]] = Field(..., description="Query results")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    query_time_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity": "users",
                "storage_type": "sql",
                "returned_count": 50,
                "data": [
                    {"id": 1, "name": "John", "email": "john@test.com"},
                    {"id": 2, "name": "Jane", "email": "jane@test.com"}
                ],
                "pagination": {
                    "limit": 50,
                    "offset": 0,
                    "has_more": True,
                    "total_count": 150
                },
                "query_time_ms": 45.2
            }
        }


# ============================================================================
# AGGREGATION MODELS
# ============================================================================

class AggregationRequest(BaseModel):
    """Request for aggregation queries"""
    entity: str = Field(..., description="Entity name")
    pipeline: List[Dict[str, Any]] = Field(
        ...,
        description="Aggregation pipeline (MongoDB-style)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity": "orders",
                "pipeline": [
                    {"$match": {"status": "completed"}},
                    {"$group": {
                        "_id": "$customer_id",
                        "total_orders": {"$sum": 1},
                        "total_amount": {"$sum": "$amount"}
                    }},
                    {"$sort": {"total_amount": -1}},
                    {"$limit": 10}
                ]
            }
        }


class AggregationResponse(BaseModel):
    """Response from aggregation endpoint"""
    entity: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type")
    result_count: int = Field(..., description="Number of results")
    results: List[Dict[str, Any]] = Field(..., description="Aggregation results")
    query_time_ms: Optional[float] = Field(None, description="Query execution time")


# ============================================================================
# ENTITY LISTING MODELS
# ============================================================================

class EntityInfo(BaseModel):
    """Information about a single entity"""
    name: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type: 'sql' or 'nosql'")
    storage_location: str = Field(..., description="Full storage location")
    record_count: int = Field(..., description="Number of records")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    version: int = Field(..., description="Schema version")


class EntitiesListResponse(BaseModel):
    """Response from entities list endpoint"""
    total_entities: int = Field(..., description="Total number of entities")
    entities: List[EntityInfo] = Field(..., description="List of entities")


# ============================================================================
# ENTITY SCHEMA MODELS
# ============================================================================

class FieldDefinition(BaseModel):
    """Definition of a single field"""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    nullable: bool = Field(..., description="Whether field can be null")
    indexed: bool = Field(default=False, description="Whether field is indexed")


class EntitySchemaResponse(BaseModel):
    """Response from entity schema endpoint"""
    entity_name: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type")
    version: int = Field(..., description="Schema version")
    fields: List[FieldDefinition] = Field(..., description="Field definitions")
    core_fields: List[str] = Field(..., description="Core/required fields")
    optional_fields: List[str] = Field(..., description="Optional fields")
    indexes: List[str] = Field(..., description="Indexed fields")
    created_at: datetime = Field(..., description="Schema creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_name": "users",
                "storage_type": "sql",
                "version": 1,
                "fields": [
                    {"name": "id", "type": "integer", "nullable": False, "indexed": True},
                    {"name": "name", "type": "string", "nullable": False, "indexed": False},
                    {"name": "email", "type": "string", "nullable": False, "indexed": True}
                ],
                "core_fields": ["id", "name", "email"],
                "optional_fields": [],
                "indexes": ["id", "email"],
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


# ============================================================================
# ENTITY STATS MODELS
# ============================================================================

class EntityStatsResponse(BaseModel):
    """Response from entity stats endpoint"""
    entity_name: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type")
    record_count: int = Field(..., description="Total number of records")
    size_bytes: Optional[int] = Field(None, description="Storage size in bytes")
    size_mb: Optional[float] = Field(None, description="Storage size in MB")
    indexes: List[str] = Field(..., description="List of indexes")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_name": "users",
                "storage_type": "sql",
                "record_count": 1500,
                "size_bytes": 2048000,
                "size_mb": 1.95,
                "indexes": ["id", "email"],
                "created_at": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T12:30:00Z",
                "last_accessed": "2024-01-16T08:45:00Z"
            }
        }


# ============================================================================
# ERROR MODELS
# ============================================================================

class QueryError(BaseModel):
    """Error response for query operations"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "EntityNotFound",
                "message": "Entity 'users' does not exist",
                "details": {
                    "available_entities": ["orders", "products"]
                }
            }
        }
