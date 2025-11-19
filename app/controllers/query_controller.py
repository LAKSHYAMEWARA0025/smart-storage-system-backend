"""
Query Controller
Handles business logic for unified query interface
"""

import time
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.services.schema_registry import SchemaRegistry
from app.services.sql_handler import SQLHandler
from app.services.nosql_handler import NoSQLHandler
from app.utils.query_translator import QueryTranslator


class QueryController:
    """
    Controller for unified query operations
    """
    
    @staticmethod
    async def query_data(
        entity: str,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Query data from entity (table or collection)
        
        Args:
            entity: Entity name (base name)
            filters: MongoDB-style filters
            sort: Sort specification
            limit: Max records to return
            offset: Records to skip
            fields: Fields to include
            
        Returns:
            Query results
        """
        try:
            start_time = time.time()
            
            # Get schema from registry
            registry = SchemaRegistry()
            schema_record = registry.find_by_name(entity)
            
            if not schema_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Entity '{entity}' not found"
                )
            
            storage_type = schema_record.storage_type
            
            # Extract actual table/collection name from storage_location
            # Format: "postgres.public.user_123_employees_v1" or "mongodb.smart_storage.user_123_orders_v1"
            actual_name = schema_record.storage_location.split('.')[-1]
            
            # Query based on storage type using actual name
            if storage_type == 'sql':
                data = await QueryController._query_sql(
                    entity=actual_name,
                    filters=filters or {},
                    sort=sort or {},
                    limit=limit,
                    offset=offset,
                    fields=fields
                )
            else:  # nosql
                data = await QueryController._query_nosql(
                    entity=actual_name,
                    filters=filters or {},
                    sort=sort or {},
                    limit=limit,
                    offset=offset,
                    fields=fields
                )
            
            # Calculate query time
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get total count (for pagination) using actual name
            total_count = await QueryController._get_total_count(
                actual_name, storage_type, filters or {}
            )
            
            # Return response with base name (entity), not actual name
            return {
                'entity': entity,
                'storage_type': storage_type,
                'returned_count': len(data),
                'data': data,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + len(data)) < total_count,
                    'total_count': total_count
                },
                'query_time_ms': round(query_time, 2)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Query failed: {str(e)}"
            )
    
    @staticmethod
    async def _query_sql(
        entity: str,
        filters: Dict[str, Any],
        sort: Dict[str, int],
        limit: int,
        offset: int,
        fields: Optional[list]
    ) -> list:
        """
        Query SQL table
        
        Args:
            entity: Table name
            filters: Filters
            sort: Sort specification
            limit: Limit
            offset: Offset
            fields: Fields to include
            
        Returns:
            List of records
        """
        from sqlalchemy import Table, MetaData, select
        from app.config import sql_engine

        metadata = MetaData()
        table = Table(entity, metadata, autoload_with=sql_engine)

        translator = QueryTranslator()

        # -----------------------------------------
        # Determine projection (always remove record_hash)
        # -----------------------------------------
        if fields:
            columns = translator.translate_projection(fields, table)
            columns = [c for c in columns if c.name != "record_hash"]
        else:
            columns = [c for c in table.c if c.name != "record_hash"]

        query = select(*columns)

        # -----------------------------------------
        # Filters
        # -----------------------------------------
        if filters:
            conditions = translator.translate_to_sql(filters, table)
            if conditions:
                query = query.where(*conditions)

        # -----------------------------------------
        # Sorting
        # -----------------------------------------
        if sort:
            order_clauses = translator.translate_sort(sort, table)
            if order_clauses:
                query = query.order_by(*order_clauses)

        # -----------------------------------------
        # Limit + offset
        # -----------------------------------------
        query = query.limit(limit).offset(offset)

        # -----------------------------------------
        # Execute
        # -----------------------------------------
        with sql_engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

            return [dict(row._mapping) for row in rows]

    
    @staticmethod
    async def _query_nosql(
        entity: str,
        filters: Dict[str, Any],
        sort: Dict[str, int],
        limit: int,
        offset: int,
        fields: Optional[list]
    ) -> list:
        """
        Query MongoDB collection
        
        Args:
            entity: Collection name
            filters: Filters
            sort: Sort specification
            limit: Limit
            offset: Offset
            fields: Fields to include
            
        Returns:
            List of documents
        """
        handler = NoSQLHandler()
        translator = QueryTranslator()
        
        # Build MongoDB query
        query = translator.build_mongodb_query(filters)
        
        # Build sort
        sort_list = translator.build_mongodb_sort(sort) if sort else None
        
        # Build projection
        projection = translator.build_mongodb_projection(fields) if fields else None
        
        # Execute query
        documents = await handler.query_documents(
            collection_name=entity,
            query=query,
            projection=projection,
            sort=sort_list,
            limit=limit,
            offset=offset
        )
        
        return documents
    
    @staticmethod
    async def _get_total_count(
        entity: str,
        storage_type: str,
        filters: Dict[str, Any]
    ) -> int:
        """
        Get total count of records matching filters
        
        Args:
            entity: Entity name
            storage_type: 'sql' or 'nosql'
            filters: Filters
            
        Returns:
            Total count
        """
        try:
            if storage_type == 'sql':
                from sqlalchemy import Table, MetaData, select, func
                from app.config import sql_engine
                
                metadata = MetaData()
                table = Table(entity, metadata, autoload_with=sql_engine)
                
                query = select(func.count()).select_from(table)
                
                if filters:
                    translator = QueryTranslator()
                    conditions = translator.translate_to_sql(filters, table)
                    if conditions:
                        query = query.where(*conditions)
                
                with sql_engine.connect() as conn:
                    result = conn.execute(query)
                    return result.scalar()
            
            else:  # nosql
                handler = NoSQLHandler()
                translator = QueryTranslator()
                query = translator.build_mongodb_query(filters)
                
                return await handler.count_documents(entity, query)
        
        except Exception:
            return 0
