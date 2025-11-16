"""
Metric Calculation Utilities
Provides functions for calculating various metrics used in storage decisions
"""

import math
from typing import Dict, List, Any, Set, Tuple
from collections import Counter


class MetricsCalculator:
    """
    Calculates metrics for storage decision making
    """
    
    @staticmethod
    def calculate_null_density(
        objects: List[Dict[str, Any]],
        unified_schema: Set[str]
    ) -> float:
        """
        Calculate null density if all objects were stored in a unified SQL table
        
        Formula: (total_null_cells / total_cells) * 100
        
        Args:
            objects: List of dictionary objects
            unified_schema: Set of all unique field names across all objects
            
        Returns:
            Null density percentage (0-100)
        """
        if not objects or not unified_schema:
            return 0.0
        
        total_cells = len(objects) * len(unified_schema)
        null_cells = 0
        
        for obj in objects:
            for field in unified_schema:
                if field not in obj or obj[field] is None:
                    null_cells += 1
        
        null_density = (null_cells / total_cells) * 100
        return round(null_density, 2)
    
    @staticmethod
    def calculate_schema_variants(objects: List[Dict[str, Any]]) -> int:
        """
        Count unique schema variants in objects
        
        Args:
            objects: List of dictionary objects
            
        Returns:
            Number of unique schema variants
        """
        if not objects:
            return 0
        
        # Create schema signatures (sorted field names)
        schema_signatures = set()
        for obj in objects:
            signature = tuple(sorted(obj.keys()))
            schema_signatures.add(signature)
        
        return len(schema_signatures)
    
    @staticmethod
    def calculate_schema_variant_threshold(num_objects: int) -> int:
        """
        Calculate maximum allowed schema variants using sqrt(N) formula
        
        Args:
            num_objects: Total number of objects
            
        Returns:
            Maximum allowed schema variants
        """
        if num_objects <= 0:
            return 0
        
        return int(math.sqrt(num_objects))
    
    @staticmethod
    def calculate_field_overlap(
        schema1: Set[str],
        schema2: Set[str]
    ) -> float:
        """
        Calculate field overlap percentage between two schemas
        
        Formula: (common_fields / total_unique_fields) * 100
        
        Args:
            schema1: Set of field names from first schema
            schema2: Set of field names from second schema
            
        Returns:
            Overlap percentage (0-100)
        """
        if not schema1 or not schema2:
            return 0.0
        
        common_fields = schema1 & schema2
        total_unique_fields = schema1 | schema2
        
        if not total_unique_fields:
            return 0.0
        
        overlap = (len(common_fields) / len(total_unique_fields)) * 100
        return round(overlap, 2)
    
    @staticmethod
    def calculate_type_distribution(
        objects: List[Dict[str, Any]],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Calculate type distribution for a specific field across all objects
        
        Args:
            objects: List of dictionary objects
            field_name: Name of the field to analyze
            
        Returns:
            Dictionary with type distribution info:
            {
                "types": {"int": 70, "str": 20, "float": 10},
                "majority_type": "int",
                "majority_count": 70,
                "total_count": 100,
                "consistency_percentage": 70.0
            }
        """
        type_counts = Counter()
        total_count = 0
        
        for obj in objects:
            if field_name in obj and obj[field_name] is not None:
                value = obj[field_name]
                value_type = type(value).__name__
                
                # Normalize type names
                if value_type == 'bool':
                    type_counts['bool'] += 1
                elif value_type in ['int', 'float']:
                    type_counts[value_type] += 1
                elif value_type == 'str':
                    # Try to detect if string is actually a number or date
                    if MetricsCalculator._is_numeric_string(value):
                        type_counts['numeric_str'] += 1
                    elif MetricsCalculator._is_datetime_string(value):
                        type_counts['datetime_str'] += 1
                    else:
                        type_counts['str'] += 1
                elif value_type == 'list':
                    type_counts['array'] += 1
                elif value_type == 'dict':
                    type_counts['object'] += 1
                else:
                    type_counts['other'] += 1
                
                total_count += 1
        
        if not type_counts:
            return {
                "types": {},
                "majority_type": None,
                "majority_count": 0,
                "total_count": 0,
                "consistency_percentage": 0.0
            }
        
        majority_type = type_counts.most_common(1)[0][0]
        majority_count = type_counts[majority_type]
        consistency_percentage = (majority_count / total_count) * 100
        
        return {
            "types": dict(type_counts),
            "majority_type": majority_type,
            "majority_count": majority_count,
            "total_count": total_count,
            "consistency_percentage": round(consistency_percentage, 2)
        }
    
    @staticmethod
    def calculate_field_cardinality(
        objects: List[Dict[str, Any]],
        field_name: str
    ) -> float:
        """
        Calculate uniqueness percentage for a field (for indexing decisions)
        
        Args:
            objects: List of dictionary objects
            field_name: Name of the field to analyze
            
        Returns:
            Cardinality percentage (0-100)
        """
        values = []
        for obj in objects:
            if field_name in obj and obj[field_name] is not None:
                values.append(obj[field_name])
        
        if not values:
            return 0.0
        
        unique_values = len(set(str(v) for v in values))
        total_values = len(values)
        
        cardinality = (unique_values / total_values) * 100
        return round(cardinality, 2)
    
    @staticmethod
    def group_objects_by_schema(
        objects: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group objects by their schema signature
        
        Args:
            objects: List of dictionary objects
            
        Returns:
            Dictionary mapping schema signature to list of objects
        """
        grouped = {}
        
        for obj in objects:
            signature = tuple(sorted(obj.keys()))
            signature_str = ",".join(signature)
            
            if signature_str not in grouped:
                grouped[signature_str] = []
            
            grouped[signature_str].append(obj)
        
        return grouped
    
    @staticmethod
    def calculate_conversion_success_rate(
        objects: List[Dict[str, Any]],
        field_name: str,
        target_type: str
    ) -> Tuple[float, List[int]]:
        """
        Calculate success rate of converting field values to target type
        
        Args:
            objects: List of dictionary objects
            field_name: Name of the field to convert
            target_type: Target type name ('int', 'float', 'str', 'datetime')
            
        Returns:
            Tuple of (success_rate_percentage, list_of_failed_indices)
        """
        from app.utils.hash_utils import TypeConverter
        
        total_attempts = 0
        successful_conversions = 0
        failed_indices = []
        
        for idx, obj in enumerate(objects):
            if field_name in obj and obj[field_name] is not None:
                value = obj[field_name]
                converted, success = TypeConverter.convert_value(value, target_type)
                
                total_attempts += 1
                if success:
                    successful_conversions += 1
                else:
                    failed_indices.append(idx)
        
        if total_attempts == 0:
            return 100.0, []
        
        success_rate = (successful_conversions / total_attempts) * 100
        return round(success_rate, 2), failed_indices
    
    @staticmethod
    def _is_numeric_string(value: str) -> bool:
        """Check if string represents a number"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _is_datetime_string(value: str) -> bool:
        """Check if string represents a datetime"""
        from dateutil import parser
        try:
            parser.parse(value)
            return True
        except (ValueError, TypeError, parser.ParserError):
            return False
    
    @staticmethod
    def calculate_all_metrics(
        objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate all relevant metrics for a dataset
        
        Args:
            objects: List of dictionary objects
            
        Returns:
            Dictionary with all calculated metrics
        """
        if not objects:
            return {
                "total_objects": 0,
                "null_density": 0.0,
                "schema_variants": 0,
                "max_allowed_variants": 0,
                "unified_schema": set(),
                "field_analysis": {}
            }
        
        # Get unified schema
        unified_schema = set()
        for obj in objects:
            unified_schema.update(obj.keys())
        
        # Calculate metrics
        null_density = MetricsCalculator.calculate_null_density(objects, unified_schema)
        schema_variants = MetricsCalculator.calculate_schema_variants(objects)
        max_allowed_variants = MetricsCalculator.calculate_schema_variant_threshold(len(objects))
        
        # Analyze each field
        field_analysis = {}
        for field in unified_schema:
            type_dist = MetricsCalculator.calculate_type_distribution(objects, field)
            cardinality = MetricsCalculator.calculate_field_cardinality(objects, field)
            
            field_analysis[field] = {
                "type_distribution": type_dist,
                "cardinality": cardinality
            }
        
        return {
            "total_objects": len(objects),
            "null_density": null_density,
            "schema_variants": schema_variants,
            "max_allowed_variants": max_allowed_variants,
            "unified_schema": unified_schema,
            "field_analysis": field_analysis
        }
