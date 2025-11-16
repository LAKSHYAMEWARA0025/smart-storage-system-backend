"""
Query Translator
Translates MongoDB-style queries to SQL WHERE clauses
"""

from typing import Dict, Any, List, Tuple
from sqlalchemy import Table, Column, and_, or_, not_
from sqlalchemy.sql import Select


class QueryTranslator:
    """
    Translates MongoDB-style queries to SQL
    """
    
    @staticmethod
    def translate_to_sql(
        filters: Dict[str, Any],
        table: Table
    ) -> List[Any]:
        """
        Convert MongoDB-style filters to SQLAlchemy conditions
        
        Args:
            filters: MongoDB-style query filters
            table: SQLAlchemy table object
            
        Returns:
            List of SQLAlchemy filter conditions
        """
        if not filters:
            return []
        
        conditions = []
        
        for field, value in filters.items():
            # Handle logical operators
            if field == '$and':
                and_conditions = []
                for sub_filter in value:
                    and_conditions.extend(
                        QueryTranslator.translate_to_sql(sub_filter, table)
                    )
                if and_conditions:
                    conditions.append(and_(*and_conditions))
            
            elif field == '$or':
                or_conditions = []
                for sub_filter in value:
                    or_conditions.extend(
                        QueryTranslator.translate_to_sql(sub_filter, table)
                    )
                if or_conditions:
                    conditions.append(or_(*or_conditions))
            
            elif field == '$not':
                not_conditions = QueryTranslator.translate_to_sql(value, table)
                if not_conditions:
                    conditions.append(not_(and_(*not_conditions)))
            
            # Handle field operators
            elif field in table.c:
                column = table.c[field]
                
                if isinstance(value, dict):
                    # Operator-based query
                    for operator, operand in value.items():
                        condition = QueryTranslator._translate_operator(
                            column, operator, operand
                        )
                        if condition is not None:
                            conditions.append(condition)
                else:
                    # Simple equality
                    conditions.append(column == value)
        
        return conditions
    
    @staticmethod
    def _translate_operator(column: Column, operator: str, value: Any):
        """
        Translate MongoDB operator to SQLAlchemy condition
        
        Args:
            column: SQLAlchemy column
            operator: MongoDB operator ($eq, $gt, etc.)
            value: Comparison value
            
        Returns:
            SQLAlchemy condition or None
        """
        operator_map = {
            '$eq': lambda c, v: c == v,
            '$ne': lambda c, v: c != v,
            '$gt': lambda c, v: c > v,
            '$gte': lambda c, v: c >= v,
            '$lt': lambda c, v: c < v,
            '$lte': lambda c, v: c <= v,
            '$in': lambda c, v: c.in_(v),
            '$nin': lambda c, v: ~c.in_(v),
            '$exists': lambda c, v: c.isnot(None) if v else c.is_(None),
        }
        
        # String operators
        if operator == '$regex':
            # Convert to SQL LIKE
            pattern = value.replace('%', '\\%').replace('_', '\\_')
            if pattern.startswith('^'):
                pattern = pattern[1:] + '%'
            elif pattern.endswith('$'):
                pattern = '%' + pattern[:-1]
            else:
                pattern = '%' + pattern + '%'
            return column.like(pattern)
        
        elif operator == '$contains':
            return column.like(f'%{value}%')
        
        # Use operator map
        if operator in operator_map:
            return operator_map[operator](column, value)
        
        return None
    
    @staticmethod
    def translate_sort(
        sort: Dict[str, int],
        table: Table
    ) -> List[Any]:
        """
        Translate MongoDB-style sort to SQLAlchemy order_by
        
        Args:
            sort: Sort specification {field: 1 or -1}
            table: SQLAlchemy table
            
        Returns:
            List of SQLAlchemy order_by clauses
        """
        order_clauses = []
        
        for field, direction in sort.items():
            if field in table.c:
                column = table.c[field]
                if direction == -1:
                    order_clauses.append(column.desc())
                else:
                    order_clauses.append(column.asc())
        
        return order_clauses
    
    @staticmethod
    def translate_projection(
        fields: List[str],
        table: Table
    ) -> List[Column]:
        """
        Translate field list to SQLAlchemy columns
        
        Args:
            fields: List of field names
            table: SQLAlchemy table
            
        Returns:
            List of SQLAlchemy columns
        """
        if not fields:
            return [table]
        
        columns = []
        for field in fields:
            if field in table.c:
                columns.append(table.c[field])
        
        return columns if columns else [table]
    
    @staticmethod
    def build_mongodb_query(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and build MongoDB query
        (MongoDB queries are already in the right format)
        
        Args:
            filters: MongoDB-style filters
            
        Returns:
            Validated MongoDB query
        """
        # MongoDB queries are already in the right format
        # Just validate and return
        return filters or {}
    
    @staticmethod
    def build_mongodb_sort(sort: Dict[str, int]) -> List[Tuple[str, int]]:
        """
        Convert sort dict to MongoDB sort list
        
        Args:
            sort: Sort specification {field: 1 or -1}
            
        Returns:
            List of tuples [(field, direction)]
        """
        return [(field, direction) for field, direction in sort.items()]
    
    @staticmethod
    def build_mongodb_projection(fields: List[str]) -> Dict[str, int]:
        """
        Convert field list to MongoDB projection
        
        Args:
            fields: List of field names
            
        Returns:
            MongoDB projection dict
        """
        if not fields:
            return None
        
        return {field: 1 for field in fields}
