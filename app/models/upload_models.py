"""
Pydantic Models for Upload API
Request and response models for structured data upload endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================================
# ANALYSIS MODELS
# ============================================================================

class MetricsInfo(BaseModel):
    """Metrics calculated during schema analysis"""
    null_density: float = Field(..., description="Null density percentage")
    schema_variants: int = Field(..., description="Number of unique schema variants")
    max_allowed_variants: int = Field(..., description="Maximum allowed variants (sqrt(N))")
    type_consistency: float = Field(..., description="Average type consistency percentage")


class ConflictInfo(BaseModel):
    """Information about schema conflicts"""
    type: str = Field(..., description="Conflict type: 'schema_evolution' or 'ambiguous'")
    existing_schema: Optional[str] = Field(None, description="Name of existing schema")
    similarity: float = Field(..., description="Similarity percentage with existing schema")
    impact: str = Field(..., description="Description of impact if schema is evolved")
    options: List[Dict[str, str]] = Field(..., description="Available options for resolution")


class SchemaDetection(BaseModel):
    """Detected schema information"""
    schema_id: str = Field(..., description="Unique identifier for this schema")
    fields: Dict[str, str] = Field(..., description="Field names to types mapping")
    record_count: int = Field(..., description="Number of records with this schema")
    storage_recommendation: str = Field(..., description="Recommended storage: 'sql' or 'nosql'")
    confidence: str = Field(..., description="Confidence level: 'high', 'medium', 'low'")
    metrics: MetricsInfo = Field(..., description="Calculated metrics")
    conflict: Optional[ConflictInfo] = Field(None, description="Conflict information if any")
    suggested_name: str = Field(..., description="Suggested table/collection name")
    reasons: List[str] = Field(default_factory=list, description="Reasons for storage decision")


class AnalysisResponse(BaseModel):
    """Response from upload analysis endpoint"""
    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    files_analyzed: int = Field(..., description="Number of files analyzed")
    schemas_detected: List[SchemaDetection] = Field(..., description="List of detected schemas")
    total_records: int = Field(..., description="Total number of records across all files")
    requires_decision: bool = Field(..., description="Whether user decision is required")


# ============================================================================
# EXECUTION MODELS
# ============================================================================

class DecisionInput(BaseModel):
    """User decision for a specific schema"""
    action: str = Field(
        ...,
        description="Action to take: 'evolve', 'new_table', 'create', 'use_nosql'"
    )
    custom_name: Optional[str] = Field(
        None,
        description="Custom name for table/collection (optional)"
    )


class ExecuteRequest(BaseModel):
    """Request to execute upload after analysis"""
    analysis_id: str = Field(..., description="Analysis ID from previous analysis")
    decisions: Dict[str, DecisionInput] = Field(
        ...,
        description="Map of schema_id to decision"
    )


class ExecuteResponse(BaseModel):
    """Response from upload execution"""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field(..., description="Job status: 'queued', 'processing'")
    message: str = Field(..., description="Status message")


# ============================================================================
# JOB STATUS MODELS
# ============================================================================

class ProgressInfo(BaseModel):
    """Job progress information"""
    current: int = Field(..., description="Current progress count")
    total: int = Field(..., description="Total items to process")
    percentage: float = Field(..., description="Progress percentage")
    stage: str = Field(..., description="Current processing stage")


class EntityCreated(BaseModel):
    """Information about created entity"""
    name: str = Field(..., description="Entity name")
    storage_type: str = Field(..., description="Storage type: 'sql' or 'nosql'")
    record_count: int = Field(..., description="Number of records stored")


class ResultInfo(BaseModel):
    """Job result information"""
    entities_created: List[EntityCreated] = Field(..., description="List of created entities")
    total_records: int = Field(..., description="Total records processed")
    successful: int = Field(..., description="Successfully stored records")
    failed: int = Field(..., description="Failed records")
    success_rate: float = Field(..., description="Success rate percentage")


class JobStatusResponse(BaseModel):
    """Response from job status endpoint"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(
        ...,
        description="Job status: 'queued', 'processing', 'completed', 'failed', 'completed_with_errors'"
    )
    progress: Optional[ProgressInfo] = Field(None, description="Progress information")
    result: Optional[ResultInfo] = Field(None, description="Result information (when completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    failed_records_url: Optional[str] = Field(None, description="URL to fetch failed records")


# ============================================================================
# FAILED RECORDS MODELS
# ============================================================================

class FailedRecordDetail(BaseModel):
    """Details of a failed record"""
    row_number: int = Field(..., description="Row number in original file")
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    original_data: Dict[str, Any] = Field(..., description="Original data that failed")


class FailedRecordsResponse(BaseModel):
    """Response from failed records endpoint"""
    job_id: str = Field(..., description="Job identifier")
    entity_name: str = Field(..., description="Entity name")
    total_failed: int = Field(..., description="Total number of failed records")
    records: List[FailedRecordDetail] = Field(..., description="List of failed records")
    expires_at: datetime = Field(..., description="When these records will be auto-deleted")


# ============================================================================
# DIRECT UPLOAD MODELS (for single endpoint)
# ============================================================================

class UploadMetadata(BaseModel):
    """Optional metadata for upload"""
    suggested_name: Optional[str] = Field(None, description="Suggested name for entity")
    preferences: Optional[Dict[str, str]] = Field(
        None,
        description="User preferences (e.g., schema_evolution: 'auto' or 'prompt')"
    )


class DirectUploadResponse(BaseModel):
    """Response from direct upload endpoint"""
    status: str = Field(
        ...,
        description="Status: 'processing', 'requires_decision', 'completed'"
    )
    job_id: Optional[str] = Field(None, description="Job ID if processing")
    analysis_id: Optional[str] = Field(None, description="Analysis ID if decision required")
    analysis: Optional[AnalysisResponse] = Field(None, description="Analysis details if decision required")
    message: str = Field(..., description="Status message")


# ============================================================================
# RETRY MODELS
# ============================================================================

class RetryRequest(BaseModel):
    """Request to retry failed records"""
    fixed_data: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Fixed data to retry (if not provided, retries with original data)"
    )


class RetryResponse(BaseModel):
    """Response from retry endpoint"""
    job_id: str = Field(..., description="New job ID for retry")
    records_to_retry: int = Field(..., description="Number of records being retried")
    message: str = Field(..., description="Status message")
