"""
Hashing and Type Conversion Utilities
Provides schema fingerprinting and data type conversion functions
"""

import hashlib
import json
from typing import Any, Tuple, Dict, Set
from datetime import datetime
from dateutil import parser as date_parser
import uuid


class HashUtils:
    """
    Utilities for generating hashes and unique identifiers
    """
    
    @staticmethod
    def generate_schema_hash(fields: Dict[str, str]) -> str:
        """
        Generate MD5 hash of schema structure
        Consistent regardless of field order
        
        Args:
            fields: Dictionary of field names to types
            
        Returns:
            MD5 hash string
        """
        # Sort fields to ensure consistent hash
        sorted_fields = sorted(fields.items())
        schema_str = json.dumps(sorted_fields, sort_keys=True)
        
        hash_obj = hashlib.md5(schema_str.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def generate_schema_fingerprint(field_names: Set[str]) -> str:
        """
        Generate a fingerprint from field names only (ignoring types)
        
        Args:
            field_names: Set of field names
            
        Returns:
            MD5 hash string
        """
        sorted_fields = sorted(field_names)
        fields_str = ",".join(sorted_fields)
        
        hash_obj = hashlib.md5(fields_str.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @staticmethod
    def generate_analysis_id() -> str:
        """
        Generate unique analysis ID
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_job_id() -> str:
        """
        Generate unique job ID
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_schema_id() -> str:
        """
        Generate unique schema ID
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_data(data: Any) -> str:
        """
        Generate hash of any data structure
        
        Args:
            data: Any JSON-serializable data
            
        Returns:
            SHA256 hash string
        """
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.sha256(data_str.encode('utf-8'))
        return hash_obj.hexdigest()


class TypeConverter:
    """
    Utilities for converting data types
    """
    
    @staticmethod
    def convert_value(value: Any, target_type: str) -> Tuple[Any, bool]:
        """
        Convert value to target type
        
        Args:
            value: Value to convert
            target_type: Target type ('int', 'float', 'str', 'datetime', 'bool')
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if target_type == 'int':
                return TypeConverter.to_int(value)
            elif target_type == 'float':
                return TypeConverter.to_float(value)
            elif target_type == 'str':
                return TypeConverter.to_str(value)
            elif target_type == 'datetime':
                return TypeConverter.to_datetime(value)
            elif target_type == 'bool':
                return TypeConverter.to_bool(value)
            else:
                return value, False
        except Exception:
            return value, False
    
    @staticmethod
    def to_int(value: Any) -> Tuple[int, bool]:
        """
        Convert value to integer
        
        Args:
            value: Value to convert
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if isinstance(value, bool):
                return int(value), True
            elif isinstance(value, (int, float)):
                return int(value), True
            elif isinstance(value, str):
                # Try direct conversion
                return int(float(value)), True
            else:
                return value, False
        except (ValueError, TypeError):
            return value, False
    
    @staticmethod
    def to_float(value: Any) -> Tuple[float, bool]:
        """
        Convert value to float
        
        Args:
            value: Value to convert
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if isinstance(value, bool):
                return float(value), True
            elif isinstance(value, (int, float)):
                return float(value), True
            elif isinstance(value, str):
                return float(value), True
            else:
                return value, False
        except (ValueError, TypeError):
            return value, False
    
    @staticmethod
    def to_str(value: Any) -> Tuple[str, bool]:
        """
        Convert value to string
        
        Args:
            value: Value to convert
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if isinstance(value, (list, dict)):
                return json.dumps(value), True
            else:
                return str(value), True
        except Exception:
            return value, False
    
    @staticmethod
    def to_datetime(value: Any) -> Tuple[datetime, bool]:
        """
        Convert value to datetime
        
        Args:
            value: Value to convert
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if isinstance(value, datetime):
                return value, True
            elif isinstance(value, str):
                parsed = date_parser.parse(value)
                return parsed, True
            elif isinstance(value, (int, float)):
                # Assume Unix timestamp
                return datetime.fromtimestamp(value), True
            else:
                return value, False
        except (ValueError, TypeError, date_parser.ParserError):
            return value, False
    
    @staticmethod
    def to_bool(value: Any) -> Tuple[bool, bool]:
        """
        Convert value to boolean
        
        Args:
            value: Value to convert
            
        Returns:
            Tuple of (converted_value, success)
        """
        try:
            if isinstance(value, bool):
                return value, True
            elif isinstance(value, (int, float)):
                return bool(value), True
            elif isinstance(value, str):
                lower_val = value.lower()
                if lower_val in ['true', '1', 'yes', 'y']:
                    return True, True
                elif lower_val in ['false', '0', 'no', 'n']:
                    return False, True
                else:
                    return value, False
            else:
                return value, False
        except Exception:
            return value, False
    
    @staticmethod
    def infer_type(value: Any) -> str:
        """
        Infer the type of a value
        
        Args:
            value: Value to analyze
            
        Returns:
            Type name string
        """
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            # Try to detect if string is actually a number or date
            if TypeConverter._is_numeric_string(value):
                return 'numeric_str'
            elif TypeConverter._is_datetime_string(value):
                return 'datetime_str'
            else:
                return 'str'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return 'other'
    
    @staticmethod
    def get_flexible_type_priority() -> Dict[str, int]:
        """
        Get type flexibility priority (higher = more flexible)
        Used for tie-breaking when types are equal
        
        Returns:
            Dictionary mapping type to priority
        """
        return {
            'str': 5,
            'float': 4,
            'int': 3,
            'bool': 2,
            'datetime': 1,
            'null': 0
        }
    
    @staticmethod
    def select_majority_type(type_counts: Dict[str, int]) -> str:
        """
        Select majority type from type distribution
        On tie, prefer more flexible type
        
        Args:
            type_counts: Dictionary of type to count
            
        Returns:
            Selected type name
        """
        if not type_counts:
            return 'str'
        
        # Find maximum count
        max_count = max(type_counts.values())
        
        # Get all types with max count (handles ties)
        tied_types = [t for t, c in type_counts.items() if c == max_count]
        
        if len(tied_types) == 1:
            return tied_types[0]
        
        # Tie-breaker: prefer more flexible type
        priority = TypeConverter.get_flexible_type_priority()
        
        # Sort by priority (descending)
        tied_types.sort(key=lambda t: priority.get(t, 0), reverse=True)
        
        return tied_types[0]
    
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
        try:
            date_parser.parse(value)
            return True
        except (ValueError, TypeError, date_parser.ParserError):
            return False


class SchemaComparator:
    """
    Utilities for comparing schemas
    """
    
    @staticmethod
    def compare_schemas(
        schema1: Dict[str, str],
        schema2: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Compare two schemas and return detailed comparison
        
        Args:
            schema1: First schema (field -> type mapping)
            schema2: Second schema (field -> type mapping)
            
        Returns:
            Dictionary with comparison details
        """
        fields1 = set(schema1.keys())
        fields2 = set(schema2.keys())
        
        common_fields = fields1 & fields2
        only_in_schema1 = fields1 - fields2
        only_in_schema2 = fields2 - fields1
        
        # Calculate overlap
        total_unique_fields = fields1 | fields2
        overlap_percentage = (len(common_fields) / len(total_unique_fields)) * 100 if total_unique_fields else 0
        
        # Check type compatibility for common fields
        type_mismatches = []
        for field in common_fields:
            if schema1[field] != schema2[field]:
                type_mismatches.append({
                    "field": field,
                    "type1": schema1[field],
                    "type2": schema2[field]
                })
        
        return {
            "overlap_percentage": round(overlap_percentage, 2),
            "common_fields": list(common_fields),
            "only_in_schema1": list(only_in_schema1),
            "only_in_schema2": list(only_in_schema2),
            "type_mismatches": type_mismatches,
            "is_compatible": len(type_mismatches) == 0
        }
