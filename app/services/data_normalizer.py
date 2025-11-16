"""
Data Normalization Service
Handles data type conversion and validation using Pydantic
"""

from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, create_model, ValidationError
from app.services.schema_analyzer import Schema, FieldInfo
from app.utils.hash_utils import TypeConverter
from app.utils.metrics import MetricsCalculator


class FailedRecord:
    """Represents a record that failed normalization"""
    
    def __init__(
        self,
        row_number: int,
        original_data: Dict[str, Any],
        error_type: str,
        error_message: str
    ):
        self.row_number = row_number
        self.original_data = original_data
        self.error_type = error_type
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'row_number': self.row_number,
            'original_data': self.original_data,
            'error_type': self.error_type,
            'error_message': self.error_message
        }


class NormalizationResult:
    """Result of data normalization"""
    
    def __init__(self):
        self.normalized_data: List[Dict[str, Any]] = []
        self.failed_records: List[FailedRecord] = []
        self.success_count: int = 0
        self.failure_count: int = 0
        self.success_rate: float = 0.0
    
    def add_success(self, data: Dict[str, Any]):
        """Add successfully normalized record"""
        self.normalized_data.append(data)
        self.success_count += 1
    
    def add_failure(self, failed_record: FailedRecord):
        """Add failed record"""
        self.failed_records.append(failed_record)
        self.failure_count += 1
    
    def calculate_success_rate(self):
        """Calculate success rate percentage"""
        total = self.success_count + self.failure_count
        if total > 0:
            self.success_rate = (self.success_count / total) * 100
        else:
            self.success_rate = 0.0


class DataNormalizer:
    """
    Normalizes data types and validates data
    """
    
    def __init__(self):
        pass
    
    def normalize_data(
        self,
        objects: List[Dict[str, Any]],
        schema: Schema
    ) -> NormalizationResult:
        """
        Main normalization function
        Converts data types and validates against schema
        
        Args:
            objects: List of objects to normalize
            schema: Target schema
            
        Returns:
            NormalizationResult with normalized data and failures
        """
        result = NormalizationResult()
        
        # Create Pydantic model from schema
        pydantic_model = self._create_pydantic_model(schema)
        
        # Normalize each object
        for idx, obj in enumerate(objects):
            try:
                # Normalize types
                normalized_obj = self._normalize_object(obj, schema)
                
                # Validate with Pydantic
                validated = pydantic_model(**normalized_obj)
                
                # Add to results
                result.add_success(validated.dict())
                
            except ValidationError as e:
                # Validation failed
                result.add_failure(FailedRecord(
                    row_number=idx,
                    original_data=obj,
                    error_type='validation_error',
                    error_message=str(e)
                ))
            except Exception as e:
                # Other errors
                result.add_failure(FailedRecord(
                    row_number=idx,
                    original_data=obj,
                    error_type='normalization_error',
                    error_message=str(e)
                ))
        
        result.calculate_success_rate()
        return result
    
    def _normalize_object(
        self,
        obj: Dict[str, Any],
        schema: Schema
    ) -> Dict[str, Any]:
        """
        Normalize a single object according to schema
        
        Args:
            obj: Object to normalize
            schema: Target schema
            
        Returns:
            Normalized object
        """
        normalized = {}
        
        for field_name, field_info in schema.fields.items():
            if field_name in obj:
                value = obj[field_name]
                
                # Skip None values
                if value is None:
                    if field_info.nullable:
                        normalized[field_name] = None
                    continue
                
                # Convert to target type
                converted_value, success = TypeConverter.convert_value(
                    value,
                    field_info.type
                )
                
                if success:
                    normalized[field_name] = converted_value
                else:
                    # Conversion failed, keep original
                    normalized[field_name] = value
            else:
                # Field missing
                if field_info.nullable:
                    normalized[field_name] = None
                # If not nullable, Pydantic will catch it
        
        return normalized
    
    def _create_pydantic_model(self, schema: Schema) -> type[BaseModel]:
        """
        Create dynamic Pydantic model from schema
        
        Args:
            schema: Schema object
            
        Returns:
            Pydantic model class
        """
        fields = {}
        
        for field_name, field_info in schema.fields.items():
            # Map type to Python type
            python_type = self._map_type_to_python(field_info.type)
            
            # Handle nullable fields
            if field_info.nullable:
                from typing import Optional
                python_type = Optional[python_type]
                fields[field_name] = (python_type, None)
            else:
                fields[field_name] = (python_type, ...)
        
        # Create model
        model = create_model('DynamicModel', **fields)
        return model
    
    def _map_type_to_python(self, type_name: str) -> type:
        """
        Map schema type to Python type
        
        Args:
            type_name: Schema type name
            
        Returns:
            Python type
        """
        type_mapping = {
            'integer': int,
            'float': float,
            'string': str,
            'boolean': bool,
            'datetime': str,  # Will be validated as datetime string
            'array': list,
            'object': dict
        }
        
        return type_mapping.get(type_name, str)
    
    def determine_majority_types(
        self,
        objects: List[Dict[str, Any]],
        schema: Schema
    ) -> Dict[str, str]:
        """
        Determine majority type for each field
        
        Args:
            objects: List of objects
            schema: Schema with field info
            
        Returns:
            Dictionary mapping field name to majority type
        """
        majority_types = {}
        
        for field_name, field_info in schema.fields.items():
            # Get type distribution
            type_dist = MetricsCalculator.calculate_type_distribution(
                objects,
                field_name
            )
            
            if type_dist['majority_type']:
                majority_types[field_name] = type_dist['majority_type']
            else:
                majority_types[field_name] = 'string'  # Default
        
        return majority_types
    
    def validate_conversion_feasibility(
        self,
        objects: List[Dict[str, Any]],
        schema: Schema
    ) -> Dict[str, Any]:
        """
        Check if type conversions are feasible
        
        Args:
            objects: List of objects
            schema: Target schema
            
        Returns:
            Dictionary with feasibility analysis
        """
        analysis = {
            'is_feasible': True,
            'field_analysis': {},
            'overall_success_rate': 0.0
        }
        
        total_success_rate = 0.0
        field_count = 0
        
        for field_name, field_info in schema.fields.items():
            # Calculate conversion success rate
            success_rate, failed_indices = MetricsCalculator.calculate_conversion_success_rate(
                objects,
                field_name,
                field_info.type
            )
            
            analysis['field_analysis'][field_name] = {
                'target_type': field_info.type,
                'success_rate': success_rate,
                'failed_count': len(failed_indices)
            }
            
            total_success_rate += success_rate
            field_count += 1
            
            # Check if field conversion is problematic
            if success_rate < 90.0:
                analysis['is_feasible'] = False
        
        # Calculate overall success rate
        if field_count > 0:
            analysis['overall_success_rate'] = total_success_rate / field_count
        
        return analysis
    
    def prepare_for_sql(
        self,
        objects: List[Dict[str, Any]],
        schema: Schema
    ) -> NormalizationResult:
        """
        Prepare data specifically for SQL storage
        Ensures all records have all fields (with NULL for missing)
        
        Args:
            objects: List of objects
            schema: Target schema
            
        Returns:
            NormalizationResult
        """
        result = NormalizationResult()
        
        for idx, obj in enumerate(objects):
            try:
                normalized_obj = {}
                
                # Ensure all fields are present
                for field_name, field_info in schema.fields.items():
                    if field_name in obj:
                        value = obj[field_name]
                        
                        # Convert type
                        if value is not None:
                            converted, success = TypeConverter.convert_value(
                                value,
                                field_info.type
                            )
                            normalized_obj[field_name] = converted if success else value
                        else:
                            normalized_obj[field_name] = None
                    else:
                        # Field missing - set to NULL
                        normalized_obj[field_name] = None
                
                result.add_success(normalized_obj)
                
            except Exception as e:
                result.add_failure(FailedRecord(
                    row_number=idx,
                    original_data=obj,
                    error_type='sql_preparation_error',
                    error_message=str(e)
                ))
        
        result.calculate_success_rate()
        return result
    
    def prepare_for_nosql(
        self,
        objects: List[Dict[str, Any]],
        schema: Schema
    ) -> NormalizationResult:
        """
        Prepare data specifically for NoSQL storage
        More flexible - keeps original structure
        
        Args:
            objects: List of objects
            schema: Target schema (for reference)
            
        Returns:
            NormalizationResult
        """
        result = NormalizationResult()
        
        for idx, obj in enumerate(objects):
            try:
                # For NoSQL, we're more permissive
                # Just ensure basic validation
                normalized_obj = dict(obj)
                
                # Optional: Try to convert types for consistency
                for field_name, field_info in schema.fields.items():
                    if field_name in normalized_obj and normalized_obj[field_name] is not None:
                        value = normalized_obj[field_name]
                        converted, success = TypeConverter.convert_value(
                            value,
                            field_info.type
                        )
                        if success:
                            normalized_obj[field_name] = converted
                
                result.add_success(normalized_obj)
                
            except Exception as e:
                result.add_failure(FailedRecord(
                    row_number=idx,
                    original_data=obj,
                    error_type='nosql_preparation_error',
                    error_message=str(e)
                ))
        
        result.calculate_success_rate()
        return result
