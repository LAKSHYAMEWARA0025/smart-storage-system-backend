"""
Pydantic Models for Media Upload API
Request and response models for media upload endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================================
# UPLOAD MODELS
# ============================================================================

class MediaUploadResponse(BaseModel):
    """Response from media upload endpoint"""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field(..., description="Job status: 'queued'")
    total_files: int = Field(..., description="Number of files queued for upload")
    message: str = Field(..., description="Status message")
    status_url: str = Field(..., description="URL to check upload status")


class FileInfo(BaseModel):
    """Information about a single uploaded file"""
    filename: str = Field(..., description="Original filename")
    url: str = Field(..., description="Storage URL")
    public_url: str = Field(..., description="Public access URL")
    size_bytes: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extracted metadata")


class ProgressInfo(BaseModel):
    """Upload progress information"""
    current: int = Field(..., description="Number of files processed")
    total: int = Field(..., description="Total number of files")
    percentage: float = Field(..., description="Progress percentage (0-100)")
    stage: str = Field(..., description="Current processing stage")


class MediaUploadStatusResponse(BaseModel):
    """Response from upload status endpoint"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status: queued, processing, completed, failed, completed_with_errors")
    progress: Optional[ProgressInfo] = Field(None, description="Progress information")
    uploaded_files: List[FileInfo] = Field(default_factory=list, description="Successfully uploaded files")
    failed_files: List[Dict[str, str]] = Field(default_factory=list, description="Failed files with errors")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
