"""
Schema Analysis Service
Analyzes JSON data to detect schemas, calculate metrics, and prepare for storage decisions
"""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from app.utils.metrics import MetricsCalculator
from app.utils.hash_utils import HashUtils, TypeConverter


@dataclass
class FieldInfo:
    """Information about a single field"""
    name: str
    type: str
    nullable: bool
    sample_values: List[Any]
    cardinality: float
    type_distribution: Dict[str, Any]


@dataclass
class Schema:
    """Represents a detected schema"""
    schema_id: str
    fields: Dict[str, FieldInfo]
    field_names: Set[str]
    record_count: int
    schema_hash: str
    has_nested_objects: bool
    has_arrays: bool


@dataclass
class SchemaAnalysis:
    """Complete analysis result for a dataset"""
    schemas: List[Schema]
    total_records: int
    unified_schema: Set[str]
    null_density: float
    schema_variants: int
    max_allowed_variants: int
    metrics: Dict[str, Any]


class SchemaAnalyzer:
    """
    Analyzes JSON data to detect schemas and calculate metrics
    """
    
    def __init__(self):
        self.metrics_calculator = MetricsCalculator()
    
    def analyze_objects(self, objects: List[Dict[str, Any]]) -> SchemaAnalysis:
        """
        Main analysis function - analyzes a list of objects
        
        Args:
            objects: List of dictionary objects to analyze
            
        Returns:
            SchemaAnalysis object with complete analysis
        """
        if not objects:
            return self._empty_analysis()
        
        # Step 1: Extract all unique schemas
        schemas = self._extract_schemas(objects)
        
        # Step 2: Get unified schema (all unique fields)
        unified_schema = set()
        for schema in schemas:
            unified_schema.update(schema.field_names)
        
        # Step 3: Calculate metrics
        null_density = MetricsCalculator.calculate_null_density(objects, unified_schema)
        schema_variants = len(schemas)
        max_allowed_variants = MetricsCalculator.calculate_schema_variant_threshold(len(objects))
        
        # Step 4: Calculate comprehensive metrics
        all_metrics = MetricsCalculator.calculate_all_metrics(objects)
        
        return SchemaAnalysis(
            schemas=schemas,
            total_records=len(objects),
            unified_schema=unified_schema,
            null_density=null_density,
            schema_variants=schema_variants,
            max_allowed_variants=max_allowed_variants,
            metrics=all_metrics
        )
    
    def _extract_schemas(self, objects: List[Dict[str, Any]]) -> List[Schema]:
        """
        Extract all unique schema variants from objects
        
        Args:
            objects: List of dictionary objects
            
        Returns:
            List of Schema objects
        """
        # Group objects by schema signature
        grouped = MetricsCalculator.group_objects_by_schema(objects)
        
        schemas = []
        for signature_str, objs in grouped.items():
            schema = self._analyze_schema_group(objs)
            schemas.append(schema)
        
        return schemas
    
    def _analyze_schema_group(self, objects: List[Dict[str, Any]]) -> Schema:
        """
        Analyze a group of objects with the same schema
        
        Args:
            objects: List of objects with same schema structure
            
        Returns:
            Schema object
        """
        if not objects:
            raise ValueError("Cannot analyze empty object list")
        
        # Get field names from first object
        field_names = set(objects[0].keys())
        
        # Analyze each field
        fields = {}
        has_nested_objects = False
        has_arrays = False
        
        for field_name in field_names:
            field_info = self._analyze_field(objects, field_name)
            fields[field_name] = field_info
            
            # Check for nested structures
            if field_info.type == 'object':
                has_nested_objects = True
            elif field_info.type == 'array':
                has_arrays = True
        
        # Generate schema hash
        field_types = {name: info.type for name, info in fields.items()}
        schema_hash = HashUtils.generate_schema_hash(field_types)
        
        # Generate schema ID
        schema_id = HashUtils.generate_schema_id()
        
        return Schema(
            schema_id=schema_id,
            fields=fields,
            field_names=field_names,
            record_count=len(objects),
            schema_hash=schema_hash,
            has_nested_objects=has_nested_objects,
            has_arrays=has_arrays
        )
    
    def _analyze_field(self, objects: List[Dict[str, Any]], field_name: str) -> FieldInfo:
        """
        Analyze a specific field across all objects
        
        Args:
            objects: List of objects
            field_name: Name of field to analyze
            
        Returns:
            FieldInfo object
        """
        # Collect values and check nullability
        values = []
        has_null = False
        
        for obj in objects:
            if field_name in obj:
                value = obj[field_name]
                if value is None:
                    has_null = True
                else:
                    values.append(value)
            else:
                has_null = True
        
        # Get type distribution
        type_dist = MetricsCalculator.calculate_type_distribution(objects, field_name)
        
        # Determine majority type
        if type_dist['majority_type']:
            majority_type = self._normalize_type_name(type_dist['majority_type'])
        else:
            majority_type = 'string'
        
        # Calculate cardinality
        cardinality = MetricsCalculator.calculate_field_cardinality(objects, field_name)
        
        # Get sample values (up to 5)
        sample_values = values[:5] if values else []
        
        return FieldInfo(
            name=field_name,
            type=majority_type,
            nullable=has_null,
            sample_values=sample_values,
            cardinality=cardinality,
            type_distribution=type_dist
        )
    
    def _normalize_type_name(self, type_name: str) -> str:
        """
        Normalize type names to standard SQL/NoSQL types
        
        Args:
            type_name: Raw type name
            
        Returns:
            Normalized type name
        """
        type_mapping = {
            'int': 'integer',
            'float': 'float',
            'str': 'string',
            'numeric_str': 'integer',  # Will be converted
            'datetime_str': 'datetime',  # Will be converted
            'bool': 'boolean',
            'array': 'array',
            'object': 'object',
            'null': 'string',  # Default for null
            'other': 'string'
        }
        
        return type_mapping.get(type_name, 'string')
    
    def _empty_analysis(self) -> SchemaAnalysis:
        """
        Return empty analysis for empty dataset
        
        Returns:
            Empty SchemaAnalysis object
        """
        return SchemaAnalysis(
            schemas=[],
            total_records=0,
            unified_schema=set(),
            null_density=0.0,
            schema_variants=0,
            max_allowed_variants=0,
            metrics={}
        )
    
    def detect_nested_structures(self, schema: Schema) -> bool:
        """
        Check if schema contains nested objects or arrays
        
        Args:
            schema: Schema object to check
            
        Returns:
            True if nested structures found
        """
        return schema.has_nested_objects or schema.has_arrays
    
    def calculate_type_consistency(self, schema: Schema) -> float:
        """
        Calculate average type consistency across all fields
        
        Args:
            schema: Schema object
            
        Returns:
            Average consistency percentage
        """
        if not schema.fields:
            return 100.0
        
        total_consistency = 0.0
        for field_info in schema.fields.values():
            consistency = field_info.type_distribution.get('consistency_percentage', 100.0)
            total_consistency += consistency
        
        avg_consistency = total_consistency / len(schema.fields)
        return round(avg_consistency, 2)
    
    def get_indexable_fields(self, schema: Schema, max_indexes: int = 5) -> List[str]:
        """
        Determine which fields should be indexed
        
        Args:
            schema: Schema object
            max_indexes: Maximum number of indexes to create
            
        Returns:
            List of field names to index
        """
        indexable = []
        
        # Priority 1: Common lookup fields
        common_fields = ['id', 'email', 'username', 'user_id']
        for field_name in common_fields:
            if field_name in schema.field_names:
                indexable.append(field_name)
        
        # Priority 2: High cardinality fields (>80% unique)
        for field_name, field_info in schema.fields.items():
            if field_name not in indexable:
                if field_info.cardinality > 80.0:
                    indexable.append(field_name)
        
        # Priority 3: Datetime fields
        for field_name, field_info in schema.fields.items():
            if field_name not in indexable:
                if field_info.type == 'datetime':
                    indexable.append(field_name)
        
        # Limit to max_indexes
        return indexable[:max_indexes]
    
    def compare_with_existing_schema(
        self,
        new_schema: Schema,
        existing_schema: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Compare new schema with existing schema
        
        Args:
            new_schema: New Schema object
            existing_schema: Existing schema (field -> type mapping)
            
        Returns:
            Comparison result dictionary
        """
        from app.utils.hash_utils import SchemaComparator
        
        # Convert new schema to field -> type mapping
        new_schema_dict = {name: info.type for name, info in new_schema.fields.items()}
        
        # Compare schemas
        comparison = SchemaComparator.compare_schemas(new_schema_dict, existing_schema)
        
        return comparison
    
    def extract_core_and_optional_fields(self, schema: Schema) -> Tuple[List[str], List[str]]:
        """
        Separate core (non-nullable) and optional (nullable) fields
        
        Args:
            schema: Schema object
            
        Returns:
            Tuple of (core_fields, optional_fields)
        """
        core_fields = []
        optional_fields = []
        
        for field_name, field_info in schema.fields.items():
            if field_info.nullable:
                optional_fields.append(field_name)
            else:
                core_fields.append(field_name)
        
        return core_fields, optional_fields
    
    def generate_schema_summary(self, schema: Schema) -> Dict[str, Any]:
        """
        Generate a summary of the schema for reporting
        
        Args:
            schema: Schema object
            
        Returns:
            Summary dictionary
        """
        core_fields, optional_fields = self.extract_core_and_optional_fields(schema)
        indexable_fields = self.get_indexable_fields(schema)
        type_consistency = self.calculate_type_consistency(schema)
        
        return {
            "schema_id": schema.schema_id,
            "schema_hash": schema.schema_hash,
            "record_count": schema.record_count,
            "total_fields": len(schema.fields),
            "core_fields": core_fields,
            "optional_fields": optional_fields,
            "has_nested_objects": schema.has_nested_objects,
            "has_arrays": schema.has_arrays,
            "type_consistency": type_consistency,
            "suggested_indexes": indexable_fields,
            "fields": {
                name: {
                    "type": info.type,
                    "nullable": info.nullable,
                    "cardinality": info.cardinality
                }
                for name, info in schema.fields.items()
            }
        }
