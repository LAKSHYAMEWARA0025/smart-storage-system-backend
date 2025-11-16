"""
Storage Decision Service
Implements SQL vs NoSQL decision logic based on defined rules
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from app.services.schema_analyzer import Schema, SchemaAnalysis
from app.config import (
    NULL_DENSITY_THRESHOLD,
    TYPE_CONSISTENCY_THRESHOLD
)


@dataclass
class StorageDecision:
    """Result of storage decision analysis"""
    storage_type: str  # "sql" or "nosql"
    confidence: str  # "high", "medium", "low"
    reasons: List[str]
    metrics: Dict[str, Any]
    passed_rules: List[str]
    failed_rules: List[str]


class StorageDecisionEngine:
    """
    Determines whether data should be stored in SQL or NoSQL
    Applies all SQL eligibility rules
    """
    
    def __init__(self):
        self.null_density_threshold = NULL_DENSITY_THRESHOLD
        self.type_consistency_threshold = TYPE_CONSISTENCY_THRESHOLD
    
    def decide_storage(self, analysis: SchemaAnalysis) -> Dict[str, StorageDecision]:
        """
        Main decision function - decides storage for each schema
        
        Args:
            analysis: SchemaAnalysis object
            
        Returns:
            Dictionary mapping schema_id to StorageDecision
        """
        decisions = {}
        
        for schema in analysis.schemas:
            decision = self._decide_for_schema(schema, analysis)
            decisions[schema.schema_id] = decision
        
        return decisions
    
    def _decide_for_schema(
        self,
        schema: Schema,
        analysis: SchemaAnalysis
    ) -> StorageDecision:
        """
        Decide storage type for a single schema
        
        Args:
            schema: Schema object
            analysis: Overall SchemaAnalysis
            
        Returns:
            StorageDecision object
        """
        reasons = []
        passed_rules = []
        failed_rules = []
        metrics = {}
        
        # Rule 1: Check for nested structures (objects/arrays)
        rule1_passed, rule1_reason = self._check_nested_structures(schema)
        if not rule1_passed:
            failed_rules.append("Rule 1: Data Structure")
            reasons.append(rule1_reason)
            return self._create_nosql_decision(reasons, metrics, passed_rules, failed_rules, "high")
        else:
            passed_rules.append("Rule 1: Data Structure")
        
        # Rule 2: Check null density
        rule2_passed, rule2_reason = self._check_null_density(analysis.null_density)
        metrics['null_density'] = analysis.null_density
        if not rule2_passed:
            failed_rules.append("Rule 2: Null Density")
            reasons.append(rule2_reason)
            return self._create_nosql_decision(reasons, metrics, passed_rules, failed_rules, "high")
        else:
            passed_rules.append("Rule 2: Null Density")
        
        # Rule 3: Check schema variants
        rule3_passed, rule3_reason = self._check_schema_variants(
            analysis.schema_variants,
            analysis.max_allowed_variants
        )
        metrics['schema_variants'] = analysis.schema_variants
        metrics['max_allowed_variants'] = analysis.max_allowed_variants
        if not rule3_passed:
            failed_rules.append("Rule 3: Schema Variants")
            reasons.append(rule3_reason)
            return self._create_nosql_decision(reasons, metrics, passed_rules, failed_rules, "high")
        else:
            passed_rules.append("Rule 3: Schema Variants")
        
        # Rule 4: Check type consistency
        rule4_passed, rule4_reason, type_consistency = self._check_type_consistency(schema)
        metrics['type_consistency'] = type_consistency
        if not rule4_passed:
            failed_rules.append("Rule 4: Type Consistency")
            reasons.append(rule4_reason)
            return self._create_nosql_decision(reasons, metrics, passed_rules, failed_rules, "medium")
        else:
            passed_rules.append("Rule 4: Type Consistency")
        
        # All rules passed - SQL is appropriate
        reasons.append("All SQL eligibility rules passed")
        reasons.append(f"Null density: {analysis.null_density}% (threshold: {self.null_density_threshold * 100}%)")
        reasons.append(f"Schema variants: {analysis.schema_variants} (max: {analysis.max_allowed_variants})")
        reasons.append(f"Type consistency: {type_consistency}% (threshold: {self.type_consistency_threshold * 100}%)")
        
        return StorageDecision(
            storage_type="sql",
            confidence="high",
            reasons=reasons,
            metrics=metrics,
            passed_rules=passed_rules,
            failed_rules=failed_rules
        )
    
    def _check_nested_structures(self, schema: Schema) -> tuple[bool, str]:
        """
        Rule 1: Check for nested objects or arrays
        
        Args:
            schema: Schema object
            
        Returns:
            Tuple of (passed, reason)
        """
        if schema.has_nested_objects:
            return False, "Data contains nested objects (not allowed in SQL)"
        
        if schema.has_arrays:
            return False, "Data contains array fields (not allowed in SQL)"
        
        return True, "Flat structure (no nested objects or arrays)"
    
    def _check_null_density(self, null_density: float) -> tuple[bool, str]:
        """
        Rule 2: Check null density threshold
        
        Args:
            null_density: Calculated null density percentage
            
        Returns:
            Tuple of (passed, reason)
        """
        threshold_percent = self.null_density_threshold * 100
        
        if null_density > threshold_percent:
            return False, f"Null density {null_density}% exceeds threshold {threshold_percent}%"
        
        return True, f"Null density {null_density}% is within acceptable range"
    
    def _check_schema_variants(
        self,
        schema_variants: int,
        max_allowed: int
    ) -> tuple[bool, str]:
        """
        Rule 3: Check schema variant threshold (sqrt(N))
        
        Args:
            schema_variants: Number of unique schema variants
            max_allowed: Maximum allowed variants
            
        Returns:
            Tuple of (passed, reason)
        """
        if schema_variants > max_allowed:
            return False, f"Schema variants {schema_variants} exceeds maximum {max_allowed}"
        
        return True, f"Schema variants {schema_variants} is within limit {max_allowed}"
    
    def _check_type_consistency(self, schema: Schema) -> tuple[bool, str, float]:
        """
        Rule 4: Check type consistency across fields
        
        Args:
            schema: Schema object
            
        Returns:
            Tuple of (passed, reason, consistency_percentage)
        """
        if not schema.fields:
            return True, "No fields to check", 100.0
        
        # Calculate average type consistency
        total_consistency = 0.0
        inconsistent_fields = []
        
        for field_name, field_info in schema.fields.items():
            consistency = field_info.type_distribution.get('consistency_percentage', 100.0)
            total_consistency += consistency
            
            if consistency < self.type_consistency_threshold * 100:
                inconsistent_fields.append(f"{field_name} ({consistency}%)")
        
        avg_consistency = total_consistency / len(schema.fields)
        threshold_percent = self.type_consistency_threshold * 100
        
        if avg_consistency < threshold_percent:
            fields_str = ", ".join(inconsistent_fields)
            return False, f"Type consistency {avg_consistency:.1f}% below threshold {threshold_percent}%. Inconsistent fields: {fields_str}", avg_consistency
        
        return True, f"Type consistency {avg_consistency:.1f}% meets threshold", avg_consistency
    
    def _create_nosql_decision(
        self,
        reasons: List[str],
        metrics: Dict[str, Any],
        passed_rules: List[str],
        failed_rules: List[str],
        confidence: str
    ) -> StorageDecision:
        """
        Create a NoSQL storage decision
        
        Args:
            reasons: List of reasons for decision
            metrics: Calculated metrics
            passed_rules: Rules that passed
            failed_rules: Rules that failed
            confidence: Confidence level
            
        Returns:
            StorageDecision object
        """
        return StorageDecision(
            storage_type="nosql",
            confidence=confidence,
            reasons=reasons,
            metrics=metrics,
            passed_rules=passed_rules,
            failed_rules=failed_rules
        )
    
    def evaluate_ambiguous_case(
        self,
        analysis: SchemaAnalysis
    ) -> Dict[str, Any]:
        """
        Evaluate cases that are on the borderline
        Provides detailed analysis for user decision
        
        Args:
            analysis: SchemaAnalysis object
            
        Returns:
            Dictionary with evaluation details
        """
        null_density = analysis.null_density
        threshold_percent = self.null_density_threshold * 100
        
        # Check if null density is close to threshold (within 5%)
        is_borderline_null = abs(null_density - threshold_percent) <= 5.0
        
        # Check if schema variants is close to limit
        is_borderline_variants = (
            analysis.schema_variants >= analysis.max_allowed_variants * 0.8
        )
        
        is_ambiguous = is_borderline_null or is_borderline_variants
        
        return {
            "is_ambiguous": is_ambiguous,
            "is_borderline_null": is_borderline_null,
            "is_borderline_variants": is_borderline_variants,
            "null_density": null_density,
            "null_threshold": threshold_percent,
            "schema_variants": analysis.schema_variants,
            "max_variants": analysis.max_allowed_variants,
            "recommendation": "Consider user preference or default to NoSQL for safety" if is_ambiguous else "Clear decision possible"
        }
    
    def get_decision_summary(self, decision: StorageDecision) -> str:
        """
        Get human-readable summary of decision
        
        Args:
            decision: StorageDecision object
            
        Returns:
            Summary string
        """
        storage_type = decision.storage_type.upper()
        confidence = decision.confidence.upper()
        
        summary = f"Storage: {storage_type} (Confidence: {confidence})\n"
        summary += f"Passed Rules: {len(decision.passed_rules)}\n"
        summary += f"Failed Rules: {len(decision.failed_rules)}\n"
        summary += "\nReasons:\n"
        for reason in decision.reasons:
            summary += f"  - {reason}\n"
        
        return summary
    
    def should_prompt_user(self, analysis: SchemaAnalysis) -> bool:
        """
        Determine if user should be prompted for decision
        
        Args:
            analysis: SchemaAnalysis object
            
        Returns:
            True if user prompt is needed
        """
        evaluation = self.evaluate_ambiguous_case(analysis)
        return evaluation['is_ambiguous']
