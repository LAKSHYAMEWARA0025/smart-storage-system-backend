"""
Schema Registry Service
Manages schema storage, retrieval, and matching in MongoDB
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from mongoengine.queryset.visitor import Q
from app.models.mongo_models import SchemaRegistryModel
from app.services.schema_analyzer import Schema
from app.utils.hash_utils import HashUtils, SchemaComparator
from app.utils.metrics import MetricsCalculator
from app.config import FIELD_OVERLAP_THRESHOLD


class SchemaRegistry:
    """
    Manages schema registry operations
    """
    
    def __init__(self):
        self.overlap_threshold = FIELD_OVERLAP_THRESHOLD
    
    def create_schema(
        self,
        schema: Schema,
        schema_name: str,
        storage_type: str,
        storage_location: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Create a new schema record in the registry
        
        Args:
            schema: Schema object from analyzer
            schema_name: Name for the schema
            storage_type: 'sql' or 'nosql'
            storage_location: Full storage location
            user_id: User who created the schema
            description: Optional description
            
        Returns:
            schema_id of created schema
        """
        # Prepare fields dictionary
        fields_dict = {}
        for field_name, field_info in schema.fields.items():
            fields_dict[field_name] = {
                'type': field_info.type,
                'nullable': field_info.nullable,
                'indexed': False  # Will be updated when indexes are created
            }
        
        # Separate core and optional fields
        core_fields = []
        optional_fields = []
        for field_name, field_info in schema.fields.items():
            if field_info.nullable:
                optional_fields.append(field_name)
            else:
                core_fields.append(field_name)
        
        # Create schema record
        schema_record = SchemaRegistryModel(
            schema_id=schema.schema_id,
            schema_name=schema_name,
            schema_hash=schema.schema_hash,
            storage_type=storage_type,
            storage_location=storage_location,
            fields=fields_dict,
            core_fields=core_fields,
            optional_fields=optional_fields,
            version=1,
            record_count=schema.record_count,
            indexes=[],
            created_by=user_id,
            description=description
        )
        
        schema_record.save()
        return schema.schema_id
    
    def find_by_hash(self, schema_hash: str) -> Optional[SchemaRegistryModel]:
        """
        Find schema by exact hash match
        
        Args:
            schema_hash: Schema hash to search for
            
        Returns:
            SchemaRegistryModel or None
        """
        try:
            return SchemaRegistryModel.objects(schema_hash=schema_hash).first()
        except Exception:
            return None
    
    def find_by_name(self, schema_name: str, version: Optional[int] = None) -> Optional[SchemaRegistryModel]:
        """
        Find schema by name and optional version
        
        Args:
            schema_name: Schema name
            version: Optional version number
            
        Returns:
            SchemaRegistryModel or None
        """
        try:
            query = {'schema_name': schema_name}
            if version is not None:
                query['version'] = version
            else:
                # Get latest version
                schemas = SchemaRegistryModel.objects(**query).order_by('-version')
                return schemas.first()
            
            return SchemaRegistryModel.objects(**query).first()
        except Exception:
            return None
    
    def find_by_name_and_user(
        self, 
        schema_name: str, 
        user_id: Optional[str] = None,
        version: Optional[int] = None
    ) -> Optional[SchemaRegistryModel]:
        """
        Find schema by name, user_id, and optional version (Phase 2: User Isolation)
        
        Args:
            schema_name: Schema name (base name, not full table name)
            user_id: User ID who owns the schema
            version: Optional version number
            
        Returns:
            SchemaRegistryModel or None
        """
        try:
            query = {'schema_name': schema_name}
            
            # Phase 2: Filter by user_id
            if user_id:
                query['created_by'] = str(user_id)
            
            if version is not None:
                query['version'] = version
            else:
                # Get latest version for this user
                schemas = SchemaRegistryModel.objects(**query).order_by('-version')
                return schemas.first()
            
            return SchemaRegistryModel.objects(**query).first()
        except Exception:
            return None
    
    def find_by_hash_and_user(
        self,
        schema_hash: str,
        user_id: Optional[str] = None
    ) -> Optional[SchemaRegistryModel]:
        """
        Find schema by hash and user_id (matches by structure, not name)
        
        Args:
            schema_hash: Schema hash (from fields structure)
            user_id: User ID who owns the schema
            
        Returns:
            Latest version of matching schema or None
        """
        try:
            query = {'schema_hash': schema_hash}
            
            # Filter by user_id
            if user_id:
                query['created_by'] = str(user_id)
            
            # Get latest version with this hash
            schemas = SchemaRegistryModel.objects(**query).order_by('-version')
            return schemas.first()
            
        except Exception as e:
            print(f"Error finding schema by hash: {e}")
            return None
    
    def find_similar(
        self,
        field_names: set,
        threshold: Optional[float] = None
    ) -> List[Tuple[SchemaRegistryModel, float]]:
        """
        Find schemas with field overlap >= threshold
        
        Args:
            field_names: Set of field names to match
            threshold: Overlap threshold (default from config)
            
        Returns:
            List of tuples (SchemaRegistryModel, similarity_score)
        """
        if threshold is None:
            threshold = self.overlap_threshold
        
        similar_schemas = []
        
        try:
            # Get all schemas
            all_schemas = SchemaRegistryModel.objects()
            
            for schema_record in all_schemas:
                # Get field names from schema
                existing_fields = set(schema_record.fields.keys())
                
                # Calculate overlap
                overlap = MetricsCalculator.calculate_field_overlap(
                    field_names,
                    existing_fields
                )
                
                # Check if meets threshold
                if overlap >= threshold * 100:  # Convert to percentage
                    similar_schemas.append((schema_record, overlap))
            
            # Sort by similarity (descending)
            similar_schemas.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            print(f"Error finding similar schemas: {e}")
        
        return similar_schemas
    
    def get_all_schemas(
        self,
        storage_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[SchemaRegistryModel]:
        """
        Get all schemas with optional filters
        
        Args:
            storage_type: Filter by storage type ('sql' or 'nosql')
            user_id: Filter by user who created
            
        Returns:
            List of SchemaRegistryModel
        """
        try:
            query = {}
            if storage_type:
                query['storage_type'] = storage_type
            if user_id:
                query['created_by'] = user_id
            
            return list(SchemaRegistryModel.objects(**query).order_by('-created_at'))
        except Exception:
            return []
    
    def update_schema(
        self,
        schema_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update existing schema record
        
        Args:
            schema_id: Schema ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        try:
            schema_record = SchemaRegistryModel.objects(schema_id=schema_id).first()
            if not schema_record:
                return False
            
            # Update allowed fields
            allowed_fields = [
                'record_count', 'indexes', 'description', 'tags',
                'fields', 'core_fields', 'optional_fields'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(schema_record, field, value)
            
            schema_record.updated_at = datetime.utcnow()
            schema_record.save()
            return True
            
        except Exception as e:
            print(f"Error updating schema: {e}")
            return False
    
    def evolve_schema(
        self,
        schema_name: str,
        new_fields: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """
        Create a new version of an existing schema
        
        Args:
            schema_name: Name of schema to evolve
            new_fields: New fields to add
            
        Returns:
            New schema_id or None
        """
        try:
            # Get latest version
            latest = self.find_by_name(schema_name)
            if not latest:
                return None
            
            # Create new version
            new_version = latest.version + 1
            new_schema_id = HashUtils.generate_schema_id()
            
            # Merge fields
            merged_fields = dict(latest.fields)
            merged_fields.update(new_fields)
            
            # Update core and optional fields
            new_core_fields = list(latest.core_fields)
            new_optional_fields = list(latest.optional_fields)
            
            for field_name, field_info in new_fields.items():
                if field_info.get('nullable', True):
                    new_optional_fields.append(field_name)
                else:
                    new_core_fields.append(field_name)
            
            # Generate new hash
            field_types = {name: info['type'] for name, info in merged_fields.items()}
            new_hash = HashUtils.generate_schema_hash(field_types)
            
            # Create new schema record
            new_schema = SchemaRegistryModel(
                schema_id=new_schema_id,
                schema_name=schema_name,
                schema_hash=new_hash,
                storage_type=latest.storage_type,
                storage_location=latest.storage_location,
                fields=merged_fields,
                core_fields=new_core_fields,
                optional_fields=new_optional_fields,
                version=new_version,
                record_count=latest.record_count,
                indexes=list(latest.indexes),
                created_by=latest.created_by,
                description=f"Evolved from v{latest.version}"
            )
            
            new_schema.save()
            return new_schema_id
            
        except Exception as e:
            print(f"Error evolving schema: {e}")
            return None
    
    def delete_schema(self, schema_id: str) -> bool:
        """
        Delete a schema from registry
        
        Args:
            schema_id: Schema ID to delete
            
        Returns:
            True if successful
        """
        try:
            schema_record = SchemaRegistryModel.objects(schema_id=schema_id).first()
            if schema_record:
                schema_record.delete()
                return True
            return False
        except Exception:
            return False
    
    def increment_record_count(self, schema_id: str, count: int) -> bool:
        """
        Increment record count for a schema
        
        Args:
            schema_id: Schema ID
            count: Number to increment by
            
        Returns:
            True if successful
        """
        try:
            schema_record = SchemaRegistryModel.objects(schema_id=schema_id).first()
            if schema_record:
                schema_record.record_count += count
                schema_record.updated_at = datetime.utcnow()
                schema_record.save()
                return True
            return False
        except Exception:
            return False
    
    def update_indexes(self, schema_id: str, indexes: List[str]) -> bool:
        """
        Update indexes for a schema
        
        Args:
            schema_id: Schema ID
            indexes: List of indexed field names
            
        Returns:
            True if successful
        """
        try:
            schema_record = SchemaRegistryModel.objects(schema_id=schema_id).first()
            if schema_record:
                schema_record.indexes = indexes
                
                # Update indexed flag in fields
                for field_name in schema_record.fields:
                    schema_record.fields[field_name]['indexed'] = field_name in indexes
                
                schema_record.updated_at = datetime.utcnow()
                schema_record.save()
                return True
            return False
        except Exception:
            return False
    
    def check_for_conflicts(
        self,
        schema: Schema,
        schema_name: str
    ) -> Dict[str, Any]:
        """
        Check if schema conflicts with existing schemas
        
        Args:
            schema: Schema object to check
            schema_name: Proposed schema name
            
        Returns:
            Dictionary with conflict information
        """
        conflicts = {
            'has_conflict': False,
            'conflict_type': None,
            'existing_schema': None,
            'similarity': 0.0,
            'recommendations': []
        }
        
        # Check for exact hash match
        exact_match = self.find_by_hash(schema.schema_hash)
        if exact_match:
            conflicts['has_conflict'] = True
            conflicts['conflict_type'] = 'exact_match'
            conflicts['existing_schema'] = exact_match.to_dict()
            conflicts['similarity'] = 100.0
            conflicts['recommendations'].append(
                f"Identical schema already exists as '{exact_match.schema_name}'. Consider using existing schema."
            )
            return conflicts
        
        # Check for similar schemas
        similar = self.find_similar(schema.field_names, threshold=self.overlap_threshold)
        
        if similar:
            best_match, similarity = similar[0]
            conflicts['has_conflict'] = True
            conflicts['conflict_type'] = 'schema_evolution'
            conflicts['existing_schema'] = best_match.to_dict()
            conflicts['similarity'] = similarity
            
            # Provide recommendations
            if similarity >= 90:
                conflicts['recommendations'].append(
                    f"Very similar to '{best_match.schema_name}' ({similarity}% match). Consider evolving existing schema."
                )
            elif similarity >= 70:
                conflicts['recommendations'].append(
                    f"Similar to '{best_match.schema_name}' ({similarity}% match). Options: evolve schema or create new table."
                )
        
        # Check for name conflict
        name_conflict = self.find_by_name(schema_name)
        if name_conflict:
            conflicts['has_conflict'] = True
            if conflicts['conflict_type'] is None:
                conflicts['conflict_type'] = 'name_conflict'
            conflicts['recommendations'].append(
                f"Name '{schema_name}' already exists. Consider using a different name or version number."
            )
        
        return conflicts
    
    def get_schema_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about schemas in registry
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_schemas = SchemaRegistryModel.objects.count()
            sql_schemas = SchemaRegistryModel.objects(storage_type='sql').count()
            nosql_schemas = SchemaRegistryModel.objects(storage_type='nosql').count()
            
            total_records = sum(
                schema.record_count for schema in SchemaRegistryModel.objects()
            )
            
            return {
                'total_schemas': total_schemas,
                'sql_schemas': sql_schemas,
                'nosql_schemas': nosql_schemas,
                'total_records': total_records,
                'avg_records_per_schema': total_records / total_schemas if total_schemas > 0 else 0
            }
        except Exception:
            return {
                'total_schemas': 0,
                'sql_schemas': 0,
                'nosql_schemas': 0,
                'total_records': 0,
                'avg_records_per_schema': 0
            }
