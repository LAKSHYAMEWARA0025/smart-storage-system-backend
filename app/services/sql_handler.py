"""
SQL Handler Service
Handles dynamic SQL table creation and operations using SQLAlchemy
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import (
    Table, Column, Integer, String, Float, Boolean,
    DateTime, Text, MetaData, Index, create_engine, inspect
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from app.services.schema_analyzer import Schema
from app.config import get_db
from datetime import datetime


class InsertResult:
    """Result of data insertion"""
    
    def __init__(self):
        self.success_count: int = 0
        self.failed_records: List[Dict[str, Any]] = []
    
    def add_success(self):
        """Increment success count"""
        self.success_count += 1
    
    def add_failure(self, row_number: int, data: Dict[str, Any], error: str):
        """Add failed record"""
        self.failed_records.append({
            'row_number': row_number,
            'data': data,
            'error': error
        })


class SQLHandler:
    """
    Handles SQL operations with dynamic table creation
    """
    
    def __init__(self):
        from app.config import sql_engine
        self.engine = sql_engine
        self.metadata = MetaData()
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists
        
        Args:
            table_name: Name of table
            
        Returns:
            True if exists
        """
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except Exception:
            return False
    
    def create_table(
        self,
        table_name: str,
        schema: Schema,
        indexes: Optional[List[str]] = None
    ) -> bool:
        """
        Dynamically create SQL table from schema
        
        Args:
            table_name: Name for the table
            schema: Schema object with field definitions
            indexes: List of field names to index
            
        Returns:
            True if successful
        """
        try:
            # Check if table already exists
            if self.table_exists(table_name):
                print(f"Table {table_name} already exists")
                return True
            
            # Create columns
            columns = []
            has_id_field = 'id' in schema.fields
            
            # Only add auto-increment id if data doesn't have one
            if not has_id_field:
                columns.append(
                    Column('id', Integer, primary_key=True, autoincrement=True)
                )
            
            for field_name, field_info in schema.fields.items():
                col_type = self._map_type_to_sql(field_info.type)
                nullable = field_info.nullable
                
                # If this is the id field from data, make it primary key
                if field_name == 'id' and has_id_field:
                    columns.append(
                        Column(field_name, col_type, primary_key=True, nullable=False)
                    )
                else:
                    columns.append(
                        Column(field_name, col_type, nullable=nullable)
                    )
            
            # Create table
            table = Table(table_name, self.metadata, *columns)
            
            # Create table in database
            table.create(self.engine, checkfirst=True)
            
            # Create indexes
            if indexes:
                self.create_indexes(table_name, indexes)
            
            print(f"✅ Table '{table_name}' created successfully")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Error creating table '{table_name}': {e}")
            return False
    
    def _map_type_to_sql(self, type_name: str):
        """
        Map schema type to SQLAlchemy type
        
        Args:
            type_name: Schema type name
            
        Returns:
            SQLAlchemy column type
        """
        type_mapping = {
            'integer': Integer,
            'float': Float,
            'string': String(255),
            'boolean': Boolean,
            'datetime': DateTime,
            'text': Text
        }
        
        return type_mapping.get(type_name, String(255))
    
    def insert_data(
        self,
        table_name: str,
        data: List[Dict[str, Any]]
    ) -> InsertResult:
        """
        Bulk insert data into table
        
        Args:
            table_name: Name of table
            data: List of dictionaries to insert
            
        Returns:
            InsertResult with success/failure counts
        """
        result = InsertResult()
        
        if not data:
            return result
        
        try:
            # Reflect existing table
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                try:
                    with self.engine.connect() as conn:
                        conn.execute(table.insert(), batch)
                        conn.commit()
                        result.success_count += len(batch)
                        
                except SQLAlchemyError as e:
                    # Batch failed, try individual inserts
                    for idx, record in enumerate(batch):
                        try:
                            with self.engine.connect() as conn:
                                conn.execute(table.insert(), [record])
                                conn.commit()
                                result.add_success()
                        except SQLAlchemyError as record_error:
                            result.add_failure(
                                i + idx,
                                record,
                                str(record_error)
                            )
            
            print(f"✅ Inserted {result.success_count} records into '{table_name}'")
            if result.failed_records:
                print(f"⚠️  {len(result.failed_records)} records failed")
            
        except Exception as e:
            print(f"❌ Error inserting data into '{table_name}': {e}")
            # Mark all as failed
            for idx, record in enumerate(data):
                result.add_failure(idx, record, str(e))
        
        return result
    
    def create_indexes(
        self,
        table_name: str,
        index_fields: List[str]
    ) -> bool:
        """
        Create indexes on specified fields
        
        Args:
            table_name: Name of table
            index_fields: List of field names to index
            
        Returns:
            True if successful
        """
        try:
            # Reflect table
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            
            # Create index for each field
            for field_name in index_fields:
                if field_name in table.c:
                    index_name = f"idx_{table_name}_{field_name}"
                    
                    # Check if index already exists
                    inspector = inspect(self.engine)
                    existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
                    
                    if index_name not in existing_indexes:
                        index = Index(index_name, table.c[field_name])
                        index.create(self.engine)
                        print(f"✅ Created index on {table_name}.{field_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating indexes on '{table_name}': {e}")
            return False
    
    def add_columns(
        self,
        table_name: str,
        new_fields: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Add new columns to existing table (schema evolution)
        
        Args:
            table_name: Name of table
            new_fields: Dictionary of field_name -> {type, nullable}
            
        Returns:
            True if successful
        """
        try:
            with self.engine.connect() as conn:
                for field_name, field_info in new_fields.items():
                    col_type = self._map_type_to_sql(field_info['type'])
                    nullable = field_info.get('nullable', True)
                    
                    # Build ALTER TABLE statement
                    sql_type = self._get_sql_type_string(field_info['type'])
                    null_clause = "NULL" if nullable else "NOT NULL"
                    
                    alter_sql = text(
                        f"ALTER TABLE {table_name} ADD COLUMN {field_name} {sql_type} {null_clause}"
                    )
                    
                    conn.execute(alter_sql)
                    conn.commit()
                    print(f"✅ Added column {field_name} to {table_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding columns to '{table_name}': {e}")
            return False
    
    def _get_sql_type_string(self, type_name: str) -> str:
        """
        Get SQL type as string for ALTER TABLE
        
        Args:
            type_name: Schema type name
            
        Returns:
            SQL type string
        """
        type_mapping = {
            'integer': 'INTEGER',
            'float': 'FLOAT',
            'string': 'VARCHAR(255)',
            'boolean': 'BOOLEAN',
            'datetime': 'TIMESTAMP',
            'text': 'TEXT'
        }
        
        return type_mapping.get(type_name, 'VARCHAR(255)')
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a table
        
        Args:
            table_name: Name of table
            
        Returns:
            Dictionary with table info or None
        """
        try:
            inspector = inspect(self.engine)
            
            if table_name not in inspector.get_table_names():
                return None
            
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            
            # Get row count
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
            
            return {
                'table_name': table_name,
                'columns': columns,
                'indexes': indexes,
                'row_count': row_count
            }
            
        except Exception as e:
            print(f"Error getting table info for '{table_name}': {e}")
            return None
    
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table
        
        Args:
            table_name: Name of table to drop
            
        Returns:
            True if successful
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                conn.commit()
                print(f"✅ Dropped table '{table_name}'")
            return True
        except Exception as e:
            print(f"❌ Error dropping table '{table_name}': {e}")
            return False
    
    def query_data(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query data from table
        
        Args:
            table_name: Name of table
            filters: Optional filter conditions
            limit: Maximum records to return
            offset: Number of records to skip
            
        Returns:
            List of records as dictionaries
        """
        try:
            # Reflect table
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            
            # Build query
            query = table.select()
            
            # Apply filters (basic implementation)
            if filters:
                for field, value in filters.items():
                    if field in table.c:
                        query = query.where(table.c[field] == value)
            
            # Apply limit and offset
            query = query.limit(limit).offset(offset)
            
            # Execute query
            with self.engine.connect() as conn:
                result = conn.execute(query)
                rows = result.fetchall()
                
                # Convert to dictionaries
                return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            print(f"Error querying table '{table_name}': {e}")
            return []
