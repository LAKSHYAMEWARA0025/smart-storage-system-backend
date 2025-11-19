"""
Entities Controller
Handles business logic for entity management
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime

from app.services.schema_registry import SchemaRegistry
from app.services.sql_handler import SQLHandler
from app.services.nosql_handler import NoSQLHandler


class EntitiesController:
    """
    Controller for entity management operations
    """
    
    @staticmethod
    async def list_entities(
        storage_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all entities (tables and collections)
        
        Args:
            storage_type: Filter by storage type ('sql' or 'nosql')
            user_id: Filter by user who created
            
        Returns:
            List of entities with metadata
        """
        try:
            registry = SchemaRegistry()
            schemas = registry.get_all_schemas(
                storage_type=storage_type,
                user_id=user_id
            )
            
            entities = []
            for schema in schemas:
                entity_info = {
                    'name': schema.schema_name,
                    'storage_type': schema.storage_type,
                    'storage_location': schema.storage_location,
                    'record_count': schema.record_count,
                    'created_at': schema.created_at.isoformat() if schema.created_at else None,
                    'updated_at': schema.updated_at.isoformat() if schema.updated_at else None,
                    'version': schema.version
                }
                entities.append(entity_info)
            
            return {
                'total_entities': len(entities),
                'entities': entities
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list entities: {str(e)}"
            )
    
    @staticmethod
    async def get_entity_schema(entity_name: str) -> Dict[str, Any]:
        """
        Get schema details for a specific entity
        
        Args:
            entity_name: Name of entity
            
        Returns:
            Schema details
        """
        try:
            registry = SchemaRegistry()
            schema = registry.find_by_name(entity_name)
            
            if not schema:
                raise HTTPException(
                    status_code=404,
                    detail=f"Entity '{entity_name}' not found"
                )
            
            # Build field definitions
            fields = []
            for field_name, field_info in schema.fields.items():
                fields.append({
                    'name': field_name,
                    'type': field_info['type'],
                    'nullable': field_info.get('nullable', True),
                    'indexed': field_info.get('indexed', False)
                })
            
            return {
                'entity_name': schema.schema_name,
                'storage_type': schema.storage_type,
                'version': schema.version,
                'fields': fields,
                'core_fields': schema.core_fields,
                'optional_fields': schema.optional_fields,
                'indexes': schema.indexes,
                'created_at': schema.created_at.isoformat() if schema.created_at else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get schema: {str(e)}"
            )
    
    @staticmethod
    async def get_entity_stats(entity_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific entity
        
        Args:
            entity_name: Name of entity
            
        Returns:
            Entity statistics
        """
        try:
            registry = SchemaRegistry()
            schema = registry.find_by_name(entity_name)
            
            if not schema:
                raise HTTPException(
                    status_code=404,
                    detail=f"Entity '{entity_name}' not found"
                )
            
            storage_type = schema.storage_type
            actual_name = schema.storage_location.split('.')[-1]
            
            # Get storage-specific stats
            if storage_type == 'sql':
                stats = await EntitiesController._get_sql_stats(actual_name)
            else:
                stats = await EntitiesController._get_nosql_stats(actual_name)
            
            # Combine with registry info
            return {
                'entity_name': entity_name,
                'storage_type': storage_type,
                'record_count': stats.get('record_count', schema.record_count),
                'size_bytes': stats.get('size_bytes'),
                'size_mb': stats.get('size_mb'),
                'indexes': schema.indexes,
                'created_at': schema.created_at.isoformat() if schema.created_at else None,
                'last_updated': schema.updated_at.isoformat() if schema.updated_at else None,
                'last_accessed': None  # Could be tracked separately
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get stats: {str(e)}"
            )
    
    @staticmethod
    async def _get_sql_stats(table_name: str) -> Dict[str, Any]:
        """
        Get statistics for SQL table
        
        Args:
            table_name: Name of table
            
        Returns:
            Table statistics
        """
        try:
            handler = SQLHandler()
            info = handler.get_table_info(table_name)
            
            if not info:
                return {'record_count': 0}
            
            return {
                'record_count': info.get('row_count', 0),
                'size_bytes': None,  # Not easily available in SQLAlchemy
                'size_mb': None
            }
            
        except Exception as e:
            print(f"Error getting SQL stats: {e}")
            return {'record_count': 0}
    
    @staticmethod
    async def _get_nosql_stats(collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for MongoDB collection
        
        Args:
            collection_name: Name of collection
            
        Returns:
            Collection statistics
        """
        try:
            handler = NoSQLHandler()
            info = await handler.get_collection_info(collection_name)
            
            if not info:
                return {'record_count': 0}
            
            size_bytes = info.get('size_bytes', 0)
            size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
            
            return {
                'record_count': info.get('document_count', 0),
                'size_bytes': size_bytes,
                'size_mb': round(size_mb, 2)
            }
            
        except Exception as e:
            print(f"Error getting NoSQL stats: {e}")
            return {'record_count': 0}
    
    @staticmethod
    async def get_registry_statistics() -> Dict[str, Any]:
        """
        Get overall registry statistics
        
        Returns:
            Registry statistics
        """
        try:
            registry = SchemaRegistry()
            stats = registry.get_schema_statistics()
            
            return stats
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get registry statistics: {str(e)}"
            )
