"""
Upload API Routes
Handles structured data upload endpoints
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional
from uuid import UUID

from app.controllers.upload_controller import UploadController
from app.models.upload_models import (
    AnalysisResponse,
    ExecuteRequest,
    ExecuteResponse,
    JobStatusResponse
)
from app.security import get_current_user


router = APIRouter()


@router.post("/data/upload/analyze", response_model=AnalysisResponse)
async def analyze_upload(
    files: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None),
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Analyze uploaded JSON files
    
    - Detects schemas
    - Calculates metrics
    - Makes storage recommendations
    - Checks for conflicts
    
    Returns analysis ID for later execution
    """
    import json
    
    # Parse metadata if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid metadata JSON"
            )
    
    result = await UploadController.analyze_upload(
        files=files,
        user_id=str(current_user_id),
        metadata=metadata_dict
    )
    
    return result


@router.post("/data/upload/execute", response_model=ExecuteResponse)
async def execute_upload(
    request: ExecuteRequest,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Execute upload based on analysis
    
    - Takes analysis_id and user decisions
    - Creates tables/collections
    - Inserts data
    - Returns job_id for tracking
    """
    result = await UploadController.execute_upload(
        analysis_id=request.analysis_id,
        decisions=request.decisions,
        user_id=str(current_user_id),
        user_override=request.user_override,
        acknowledge_risks=request.acknowledge_risks
    )
    
    return result


@router.get("/data/upload/status/{job_id}", response_model=JobStatusResponse)
async def get_upload_status(
    job_id: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get upload job status
    
    - Returns current status
    - Progress information
    - Results when completed
    """
    result = await UploadController.get_job_status(job_id)
    
    return result


@router.get("/data/upload/{job_id}/failed")
async def get_failed_records(
    job_id: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get failed records for a job
    
    Returns list of records that failed to insert
    """
    from app.models.mongo_models import FailedRecordModel
    
    failed_records = FailedRecordModel.objects(upload_job_id=job_id)
    
    return {
        'job_id': job_id,
        'total_failed': failed_records.count(),
        'records': [record.to_dict() for record in failed_records]
    }
