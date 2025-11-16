"""
Naming Service
Generates appropriate names for tables and collections
"""

import re
import time
from typing import Optional, List, Set
from app.services.schema_analyzer import Schema


class NamingService:
    """
    Generates names for tables and collections
    """
    
    # Generic names to avoid
    GENERIC_NAMES = {
        'data', 'file', 'download', 'upload', 'temp', 'new',
        'document', 'item', 'object', 'record', 'entry'
    }
    
    # Common field patterns that suggest entity names
    FIELD_PATTERNS = {
        'user': ['user_id', 'username', 'email', 'password'],
        'product': ['product_id', 'product_name', 'price', 'sku'],
        'order': ['order_id', 'customer_id', 'order_date'],
        'customer': ['customer_id', 'customer_name', 'customer_email'],
        'employee': ['employee_id', 'employee_name', 'department'],
        'transaction': ['transaction_id', 'amount', 'transaction_date'],
        'invoice': ['invoice_id', 'invoice_number', 'invoice_date'],
        'payment': ['payment_id', 'payment_method', 'payment_date'],
        'address': ['street', 'city', 'state', 'zip', 'country'],
        'contact': ['contact_id', 'phone', 'email', 'address']
    }
    
    def __init__(self):
        pass
    
    def generate_name(
        self,
        schema: Schema,
        file_name: Optional[str] = None,
        user_suggested: Optional[str] = None,
        existing_names: Optional[List[str]] = None
    ) -> str:
        """
        Generate appropriate name for table/collection
        
        Priority:
        1. User-provided name (if valid)
        2. Filename (if meaningful)
        3. Field-based inference (limited patterns)
        4. Fallback: data_{timestamp}_{hash}
        
        Args:
            schema: Schema object
            file_name: Original filename (optional)
            user_suggested: User-suggested name (optional)
            existing_names: List of existing entity names
            
        Returns:
            Generated name
        """
        existing_names = existing_names or []
        
        # Priority 1: User-suggested name
        if user_suggested:
            sanitized = self.sanitize_name(user_suggested)
            if self.is_meaningful_name(sanitized):
                return self.ensure_unique(sanitized, existing_names)
        
        # Priority 2: Extract from filename
        if file_name:
            name_from_file = self.extract_from_filename(file_name)
            if name_from_file:
                return self.ensure_unique(name_from_file, existing_names)
        
        # Priority 3: Infer from field names
        inferred_name = self.infer_from_fields(schema.field_names)
        if inferred_name:
            return self.ensure_unique(inferred_name, existing_names)
        
        # Priority 4: Fallback to generated name
        fallback_name = self.generate_fallback_name(schema.schema_hash)
        return self.ensure_unique(fallback_name, existing_names)
    
    def extract_from_filename(self, file_name: str) -> Optional[str]:
        """
        Extract meaningful name from filename
        
        Args:
            file_name: Original filename
            
        Returns:
            Extracted name or None
        """
        # Remove extension
        name = file_name.lower()
        for ext in ['.json', '.zip', '.txt', '.csv']:
            name = name.replace(ext, '')
        
        # Sanitize
        name = self.sanitize_name(name)
        
        # Check if meaningful
        if self.is_meaningful_name(name):
            return name
        
        return None
    
    def infer_from_fields(self, field_names: Set[str]) -> Optional[str]:
        """
        Infer entity name from field names
        Only matches obvious patterns
        
        Args:
            field_names: Set of field names
            
        Returns:
            Inferred name or None
        """
        field_names_lower = {name.lower() for name in field_names}
        
        # Check each pattern
        best_match = None
        best_match_count = 0
        
        for entity_name, pattern_fields in self.FIELD_PATTERNS.items():
            # Count how many pattern fields are present
            match_count = sum(1 for field in pattern_fields if field in field_names_lower)
            
            # If at least 2 pattern fields match, consider it
            if match_count >= 2 and match_count > best_match_count:
                best_match = entity_name
                best_match_count = match_count
        
        # Pluralize if found
        if best_match:
            return self.pluralize(best_match)
        
        return None
    
    def generate_fallback_name(self, schema_hash: str) -> str:
        """
        Generate fallback name using timestamp and hash
        
        Args:
            schema_hash: Schema hash string
            
        Returns:
            Generated name
        """
        timestamp = int(time.time())
        hash_prefix = schema_hash[:6]
        return f"data_{timestamp}_{hash_prefix}"
    
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize name to be database-safe
        - Lowercase
        - Alphanumeric and underscore only
        - Cannot start with number
        
        Args:
            name: Raw name
            
        Returns:
            Sanitized name
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces and hyphens with underscores
        name = name.replace(' ', '_').replace('-', '_')
        
        # Remove all non-alphanumeric characters except underscore
        name = re.sub(r'[^a-z0-9_]', '', name)
        
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Ensure doesn't start with number
        if name and name[0].isdigit():
            name = 'n_' + name
        
        # Ensure not empty
        if not name:
            name = 'entity'
        
        return name
    
    def is_meaningful_name(self, name: str) -> bool:
        """
        Check if name is meaningful (not generic)
        
        Args:
            name: Name to check
            
        Returns:
            True if meaningful
        """
        if not name or len(name) < 2:
            return False
        
        # Check against generic names
        if name in self.GENERIC_NAMES:
            return False
        
        # Check if it's just numbers
        if name.replace('_', '').isdigit():
            return False
        
        return True
    
    def ensure_unique(self, name: str, existing_names: List[str]) -> str:
        """
        Ensure name is unique by adding suffix if needed
        
        Args:
            name: Proposed name
            existing_names: List of existing names
            
        Returns:
            Unique name
        """
        if name not in existing_names:
            return name
        
        # Try adding numbers
        counter = 1
        while f"{name}_{counter}" in existing_names:
            counter += 1
        
        return f"{name}_{counter}"
    
    def pluralize(self, word: str) -> str:
        """
        Simple pluralization (English)
        
        Args:
            word: Singular word
            
        Returns:
            Plural form
        """
        # Already plural
        if word.endswith('s'):
            return word
        
        # Special cases
        special_cases = {
            'person': 'people',
            'child': 'children',
            'man': 'men',
            'woman': 'women',
            'tooth': 'teeth',
            'foot': 'feet',
            'mouse': 'mice',
            'goose': 'geese'
        }
        
        if word in special_cases:
            return special_cases[word]
        
        # Words ending in 'y'
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            return word[:-1] + 'ies'
        
        # Words ending in 's', 'x', 'z', 'ch', 'sh'
        if word.endswith(('s', 'x', 'z')) or word.endswith(('ch', 'sh')):
            return word + 'es'
        
        # Default: add 's'
        return word + 's'
    
    def suggest_alternative_names(
        self,
        schema: Schema,
        primary_name: str,
        count: int = 3
    ) -> List[str]:
        """
        Suggest alternative names for a schema
        
        Args:
            schema: Schema object
            primary_name: Primary suggested name
            count: Number of alternatives to suggest
            
        Returns:
            List of alternative names
        """
        alternatives = []
        
        # Try different field-based inferences
        field_names_lower = {name.lower() for name in schema.field_names}
        
        # Look for ID fields
        for field in field_names_lower:
            if field.endswith('_id') and field != 'id':
                entity = field[:-3]  # Remove '_id'
                alternatives.append(self.pluralize(entity))
        
        # Look for name fields
        for field in field_names_lower:
            if field.endswith('_name'):
                entity = field[:-5]  # Remove '_name'
                alternatives.append(self.pluralize(entity))
        
        # Add generic alternatives
        alternatives.append(f"{primary_name}_data")
        alternatives.append(f"{primary_name}_records")
        
        # Remove duplicates and limit
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt not in seen and alt != primary_name:
                seen.add(alt)
                unique_alternatives.append(alt)
                if len(unique_alternatives) >= count:
                    break
        
        return unique_alternatives
    
    def validate_name(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate if a name is acceptable
        
        Args:
            name: Name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if len(name) < 2:
            return False, "Name must be at least 2 characters long"
        
        if len(name) > 64:
            return False, "Name must be at most 64 characters long"
        
        # Check format
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            return False, "Name must start with a letter and contain only lowercase letters, numbers, and underscores"
        
        # Check if generic
        if name in self.GENERIC_NAMES:
            return False, f"Name '{name}' is too generic. Please choose a more specific name"
        
        return True, None
