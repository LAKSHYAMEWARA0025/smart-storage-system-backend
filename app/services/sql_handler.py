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
        indexes: Optional[List[str]] = None,
        add_record_hash: bool = True
    ) -> bool:
        """
        Dynamically create SQL table from schema
        
        Args:
            table_name: Name for the table
            schema: Schema object with field definitions
            indexes: List of field names to index
            add_record_hash: Add record_hash column for duplicate detection
            
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
            
            # Add record_hash column for duplicate detection
            if add_record_hash:
                columns.append(
                    Column('record_hash', String(64), nullable=True, index=True)
                )
            
            # Add metadata columns (only if not already in schema)
            if 'created_at' not in schema.fields:
                columns.append(Column('created_at', DateTime, default=datetime.utcnow))
            if 'updated_at' not in schema.fields:
                columns.append(Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))
            
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
    
    def _calculate_record_hash(self, record: Dict[str, Any]) -> str:
        """
        Calculate hash of record for duplicate detection
        
        Args:
            record: Record dictionary
            
        Returns:
            SHA-256 hash string
        """
        import hashlib
        import json
        
        # Exclude metadata fields from hash
        clean_record = {k: v for k, v in record.items() 
                       if k not in ['created_at', 'updated_at', 'record_hash']}
        
        # Sort keys for consistent hashing
        record_str = json.dumps(clean_record, sort_keys=True, default=str)
        return hashlib.sha256(record_str.encode()).hexdigest()
    
    def insert_data(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        skip_duplicates: bool = True
    ) -> InsertResult:
        """
        Bulk insert data into table with duplicate detection
        
        Args:
            table_name: Name of table
            data: List of dictionaries to insert
            skip_duplicates: If True, skip records with same hash
            
        Returns:
            InsertResult with success/failure counts
        """
        result = InsertResult()
        
        if not data:
            return result
        
        try:
            # Reflect existing table
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            
            # Check if table has record_hash column
            has_hash_column = 'record_hash' in [col.name for col in table.columns]
            
            # Get primary key columns
            pk_columns = [col.name for col in table.primary_key.columns]
            
            # Add record hashes and timestamps to data
            for record in data:
                if has_hash_column:
                    record['record_hash'] = self._calculate_record_hash(record)
                if 'created_at' not in record:
                    record['created_at'] = datetime.utcnow()
                if 'updated_at' not in record:
                    record['updated_at'] = datetime.utcnow()
            
            # If skip_duplicates, check for existing hashes
            skipped_count = 0
            updated_count = 0
            
            if skip_duplicates and has_hash_column and pk_columns:
                with self.engine.connect() as conn:
                    filtered_data = []
                    
                    for record in data:
                        # Check if record with same PK exists
                        pk_values = {pk: record.get(pk) for pk in pk_columns if pk in record}
                        
                        if pk_values:
                            # Build WHERE clause for primary key
                            where_clauses = [f"{pk} = :{pk}" for pk in pk_values.keys()]
                            where_sql = " AND ".join(where_clauses)
                            
                            # Check if exists with same hash
                            check_query = text(
                                f"SELECT record_hash FROM {table_name} WHERE {where_sql}"
                            )
                            existing = conn.execute(check_query, pk_values).fetchone()
                            
                            if existing:
                                existing_hash = existing[0]
                                if existing_hash == record['record_hash']:
                                    # Exact duplicate - skip
                                    skipped_count += 1
                                    continue
                                else:
                                    # Same PK, different data - update
                                    update_cols = {k: v for k, v in record.items() if k not in pk_columns}
                                    update_cols['updated_at'] = datetime.utcnow()
                                    
                                    set_clauses = [f"{k} = :{k}" for k in update_cols.keys()]
                                    set_sql = ", ".join(set_clauses)
                                    
                                    update_query = text(
                                        f"UPDATE {table_name} SET {set_sql} WHERE {where_sql}"
                                    )
                                    conn.execute(update_query, {**update_cols, **pk_values})
                                    updated_count += 1
                                    continue
                        
                        # New record - add to insert list
                        filtered_data.append(record)
                    
                    conn.commit()
                    data = filtered_data
                    
                    if skipped_count > 0:
                        print(f"⏭️  Skipped {skipped_count} exact duplicates")
                    if updated_count > 0:
                        print(f"🔄 Updated {updated_count} existing records")
            
            if not data:
                result.success_count = updated_count
                print(f"✅ No new records to insert (skipped: {skipped_count}, updated: {updated_count})")
                return result
            
            # Insert new records in batches
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
            
            total_success = result.success_count + updated_count
            print(f"✅ Processed {total_success} records into '{table_name}' (inserted: {result.success_count}, updated: {updated_count}, skipped: {skipped_count})")
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
    
    def copy_table_data(
        self,
        source_table: str,
        target_table: str,
        new_fields: set = None
    ) -> bool:
        """
        Copy all data from source table to target table (Phase 3: Schema Evolution)
        New fields will be NULL in copied records
        
        Args:
            source_table: Source table name (e.g., user_123_employees_v1)
            target_table: Target table name (e.g., user_123_employees_v2)
            new_fields: Set of new field names (will be NULL)
            
        Returns:
            True if successful
        """
        try:
            # Check if source table exists
            if not self.table_exists(source_table):
                print(f"⚠️  Source table '{source_table}' does not exist")
                return False
            
            # Get source table columns
            inspector = inspect(self.engine)
            source_columns = [col['name'] for col in inspector.get_columns(source_table)]
            
            # Exclude metadata columns that will be auto-generated
            exclude_cols = {'created_at', 'updated_at'}
            copy_columns = [col for col in source_columns if col not in exclude_cols]
            
            # Build column list for INSERT
            columns_str = ', '.join(copy_columns)
            
            # Copy data
            with self.engine.connect() as conn:
                # Get count first
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {source_table}"))
                total_records = count_result.scalar()
                
                if total_records == 0:
                    print(f"ℹ️  Source table '{source_table}' is empty")
                    return True
                
                print(f"📊 Copying {total_records} records from {source_table} to {target_table}")
                
                # Copy data (new fields will be NULL automatically)
                copy_sql = text(f"""
                    INSERT INTO {target_table} ({columns_str})
                    SELECT {columns_str}
                    FROM {source_table}
                """)
                
                conn.execute(copy_sql)
                conn.commit()
                
                print(f"✅ Copied {total_records} records successfully")
                
                if new_fields:
                    print(f"   New fields (NULL for migrated records): {new_fields}")
                
                return True
                
        except Exception as e:
            print(f"❌ Error copying data from '{source_table}' to '{target_table}': {e}")
            return False
    
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
