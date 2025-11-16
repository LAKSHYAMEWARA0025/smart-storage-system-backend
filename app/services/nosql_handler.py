"""
NoSQL Handler Service
Handles dynamic MongoDB collection creation and operations using Motor
"""

from typing import List, Dict, Any, Optional
from pymongo.errors import PyMongoError, BulkWriteError
from app.services.schema_analyzer import Schema
from app.config import get_mongodb


class InsertResult:
    """Result of data insertion"""
    
    def __init__(self):
        self.success_count: int = 0
        self.failed_records: List[Dict[str, Any]] = []
    
    def add_success(self, count: int = 1):
        """Increment success count"""
        self.success_count += count
    
    def add_failure(self, row_number: int, data: Dict[str, Any], error: str):
        """Add failed record"""
        self.failed_records.append({
            'row_number': row_number,
            'data': data,
            'error': error
        })


class NoSQLHandler:
    """
    Handles MongoDB operations with dynamic collection creation
    """
    
    def __init__(self):
        self.db = get_mongodb()
    
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if collection exists
        
        Args:
            collection_name: Name of collection
            
        Returns:
            True if exists
        """
        try:
            collections = await self.db.list_collection_names()
            return collection_name in collections
        except Exception:
            return False
    
    async def create_collection(
        self,
        collection_name: str,
        schema: Schema,
        indexes: Optional[List[str]] = None
    ) -> bool:
        """
        Create MongoDB collection with indexes
        
        Args:
            collection_name: Name for the collection
            schema: Schema object (for reference)
            indexes: List of field names to index
            
        Returns:
            True if successful
        """
        try:
            # Check if collection already exists
            if await self.collection_exists(collection_name):
                print(f"Collection {collection_name} already exists")
                return True
            
            # Create collection
            await self.db.create_collection(collection_name)
            
            # Create indexes
            if indexes:
                await self.create_indexes(collection_name, indexes)
            
            print(f"✅ Collection '{collection_name}' created successfully")
            return True
            
        except PyMongoError as e:
            print(f"❌ Error creating collection '{collection_name}': {e}")
            return False
    
    async def insert_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]]
    ) -> InsertResult:
        """
        Bulk insert documents into collection
        
        Args:
            collection_name: Name of collection
            documents: List of documents to insert
            
        Returns:
            InsertResult with success/failure counts
        """
        result = InsertResult()
        
        if not documents:
            return result
        
        try:
            collection = self.db[collection_name]
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    insert_result = await collection.insert_many(
                        batch,
                        ordered=False  # Continue on error
                    )
                    result.add_success(len(insert_result.inserted_ids))
                    
                except BulkWriteError as e:
                    # Some documents succeeded, some failed
                    result.add_success(e.details.get('nInserted', 0))
                    
                    # Track failed documents
                    for error in e.details.get('writeErrors', []):
                        idx = error.get('index', 0)
                        result.add_failure(
                            i + idx,
                            batch[idx],
                            error.get('errmsg', 'Unknown error')
                        )
                
                except PyMongoError as e:
                    # Entire batch failed, try individual inserts
                    for idx, doc in enumerate(batch):
                        try:
                            await collection.insert_one(doc)
                            result.add_success()
                        except PyMongoError as doc_error:
                            result.add_failure(
                                i + idx,
                                doc,
                                str(doc_error)
                            )
            
            print(f"✅ Inserted {result.success_count} documents into '{collection_name}'")
            if result.failed_records:
                print(f"⚠️  {len(result.failed_records)} documents failed")
            
        except Exception as e:
            print(f"❌ Error inserting documents into '{collection_name}': {e}")
            # Mark all as failed
            for idx, doc in enumerate(documents):
                result.add_failure(idx, doc, str(e))
        
        return result
    
    async def create_indexes(
        self,
        collection_name: str,
        index_fields: List[str]
    ) -> bool:
        """
        Create indexes on specified fields
        
        Args:
            collection_name: Name of collection
            index_fields: List of field names to index
            
        Returns:
            True if successful
        """
        try:
            collection = self.db[collection_name]
            
            # Create index for each field
            for field_name in index_fields:
                await collection.create_index(field_name)
                print(f"✅ Created index on {collection_name}.{field_name}")
            
            # Create compound index on core fields if multiple
            if len(index_fields) > 1:
                compound_index = [(field, 1) for field in index_fields[:3]]  # Max 3 fields
                await collection.create_index(compound_index)
                print(f"✅ Created compound index on {collection_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating indexes on '{collection_name}': {e}")
            return False
    
    async def get_collection_info(
        self,
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection
        
        Args:
            collection_name: Name of collection
            
        Returns:
            Dictionary with collection info or None
        """
        try:
            if not await self.collection_exists(collection_name):
                return None
            
            collection = self.db[collection_name]
            
            # Get document count
            doc_count = await collection.count_documents({})
            
            # Get indexes
            indexes = await collection.list_indexes().to_list(length=None)
            
            # Get sample document for schema inference
            sample_doc = await collection.find_one()
            
            # Get collection stats
            stats = await self.db.command('collStats', collection_name)
            
            return {
                'collection_name': collection_name,
                'document_count': doc_count,
                'indexes': [idx['name'] for idx in indexes],
                'size_bytes': stats.get('size', 0),
                'storage_size_bytes': stats.get('storageSize', 0),
                'sample_fields': list(sample_doc.keys()) if sample_doc else []
            }
            
        except Exception as e:
            print(f"Error getting collection info for '{collection_name}': {e}")
            return None
    
    async def drop_collection(self, collection_name: str) -> bool:
        """
        Drop a collection
        
        Args:
            collection_name: Name of collection to drop
            
        Returns:
            True if successful
        """
        try:
            await self.db.drop_collection(collection_name)
            print(f"✅ Dropped collection '{collection_name}'")
            return True
        except Exception as e:
            print(f"❌ Error dropping collection '{collection_name}': {e}")
            return False
    
    async def query_documents(
        self,
        collection_name: str,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query documents from collection
        
        Args:
            collection_name: Name of collection
            query: MongoDB query filter
            projection: Fields to include/exclude
            sort: Sort specification
            limit: Maximum documents to return
            offset: Number of documents to skip
            
        Returns:
            List of documents
        """
        try:
            collection = self.db[collection_name]
            
            # Build query
            cursor = collection.find(
                query or {},
                projection=projection
            )
            
            # Apply sort
            if sort:
                cursor = cursor.sort(sort)
            
            # Apply skip and limit
            cursor = cursor.skip(offset).limit(limit)
            
            # Execute and return
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return documents
            
        except Exception as e:
            print(f"Error querying collection '{collection_name}': {e}")
            return []
    
    async def update_documents(
        self,
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> int:
        """
        Update documents matching query
        
        Args:
            collection_name: Name of collection
            query: Query filter
            update: Update operations
            
        Returns:
            Number of documents updated
        """
        try:
            collection = self.db[collection_name]
            result = await collection.update_many(query, update)
            return result.modified_count
        except Exception as e:
            print(f"Error updating documents in '{collection_name}': {e}")
            return 0
    
    async def delete_documents(
        self,
        collection_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Delete documents matching query
        
        Args:
            collection_name: Name of collection
            query: Query filter
            
        Returns:
            Number of documents deleted
        """
        try:
            collection = self.db[collection_name]
            result = await collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            print(f"Error deleting documents from '{collection_name}': {e}")
            return 0
    
    async def aggregate(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run aggregation pipeline
        
        Args:
            collection_name: Name of collection
            pipeline: Aggregation pipeline
            
        Returns:
            List of aggregation results
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return results
            
        except Exception as e:
            print(f"Error running aggregation on '{collection_name}': {e}")
            return []
    
    async def count_documents(
        self,
        collection_name: str,
        query: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count documents matching query
        
        Args:
            collection_name: Name of collection
            query: Query filter
            
        Returns:
            Document count
        """
        try:
            collection = self.db[collection_name]
            return await collection.count_documents(query or {})
        except Exception as e:
            print(f"Error counting documents in '{collection_name}': {e}")
            return 0
