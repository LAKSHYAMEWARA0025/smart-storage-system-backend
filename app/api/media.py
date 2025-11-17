"""
Media Upload API Routes
Handles media file upload endpoints with background processing
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.models.media_models import MediaUploadResponse, MediaUploadStatusResponse, ProgressInfo, FileInfo
from app.models.mongo_models import MediaUploadJobModel
from app.services.media_handler import MediaHandler
from app.workers.media_worker import process_media_upload_task
from app.security import get_current_user
from app.utils.hash_utils import HashUtils
from app.config import (
    MAX_MEDIA_FILE_SIZE,
    MAX_FILES_PER_UPLOAD
)


router = APIRouter()


# Allowed media types
ALLOWED_MEDIA_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
    'video/webm'
]


@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    files: List[UploadFile] = File(...),
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Upload media files with background processing
    
    - Accepts multiple image/video files
    - Validates file types and sizes
    - Queues upload job for background processing
    - Returns job_id for status tracking
    """
    user_id = str(current_user_id)
    
    try:
        # Validate number of files
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {MAX_FILES_PER_UPLOAD} files allowed per upload."
            )
        
        if len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        # Initialize media handler for validation
        media_handler = MediaHandler()
        
        # Read and validate files
        files_data = []
        total_size = 0
        
        for file in files:
            # Read file content
            content = await file.read()
            file_size = len(content)
            total_size += file_size
            
            # Validate file
            is_valid, error_msg = media_handler.validate_file(
                filename=file.filename,
                size=file_size,
                content_type=file.content_type,
                max_size_mb=MAX_MEDIA_FILE_SIZE // (1024 * 1024),
                allowed_types=ALLOWED_MEDIA_TYPES
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}': {error_msg}"
                )
            
            # Store file data for worker
            files_data.append({
                'filename': file.filename,
                'content_type': file.content_type,
                'size': file_size,
                'data': content  # Raw bytes
            })
            
            print(f"📁 Queued file: {file.filename} ({file_size / 1024:.2f} KB)")
        
        print(f"📊 Total upload size: {total_size / 1024 / 1024:.2f} MB")
        
        # Create job in database
        job_id = HashUtils.generate_job_id()
        
        # Store file data in MongoDB GridFS asynchronously (to avoid large Celery messages)
        from app.config import get_mongodb
        from motor import motor_asyncio
        import gridfs
        
        mongodb = get_mongodb()
        fs = motor_asyncio.AsyncIOMotorGridFSBucket(mongodb)
        
        files_metadata = []
        for file_info in files_data:
            # Store file in GridFS asynchronously
            file_id = await fs.upload_from_stream(
                file_info['filename'],
                file_info['data'],
                metadata={
                    'content_type': file_info['content_type'],
                    'job_id': job_id
                }
            )
            
            files_metadata.append({
                'file_id': str(file_id),
                'filename': file_info['filename'],
                'content_type': file_info['content_type'],
                'size': file_info['size']
            })
            
            print(f"💾 Stored in GridFS: {file_info['filename']} (ID: {file_id})")
        
        job = MediaUploadJobModel(
            job_id=job_id,
            user_id=user_id,
            status='queued',
            progress_total=len(files_metadata),
            total_files=len(files_metadata),
            progress_stage='queued'
        )
        job.save()
        
        print(f"✅ Created media upload job: {job_id}")
        
        # Queue Celery task with file metadata only (not raw bytes)
        try:
            task = process_media_upload_task.delay(
                job_id=job_id,
                files_metadata=files_metadata,
                user_id=user_id
            )
            print(f"🚀 Queued background task for job: {job_id}")
            print(f"   Task ID: {task.id}")
            print(f"   Task State: {task.state}")
        except Exception as queue_error:
            print(f"❌ Failed to queue task: {queue_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue upload task: {str(queue_error)}"
            )
        
        # Return response immediately
        return MediaUploadResponse(
            job_id=job_id,
            status='queued',
            total_files=len(files_data),
            message=f'Upload queued for processing. {len(files_data)} file(s) will be uploaded.',
            status_url=f'/api/media/upload/status/{job_id}'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Media upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/media/upload/status/{job_id}", response_model=MediaUploadStatusResponse)
async def get_upload_status(
    job_id: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get media upload job status
    
    - Returns current progress and status
    - Shows uploaded files and any errors
    - Poll this endpoint to track upload progress
    """
    user_id = str(current_user_id)
    
    try:
        # Get job from database
        job = MediaUploadJobModel.objects(job_id=job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Upload job not found"
            )
        
        # Verify user owns this job
        if job.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        # Build progress info
        progress = None
        if job.progress_total > 0:
            progress = ProgressInfo(
                current=job.progress_current,
                total=job.progress_total,
                percentage=job.progress_percentage,
                stage=job.progress_stage
            )
        
        # Build file info list
        uploaded_files = [
            FileInfo(**file_data) for file_data in job.uploaded_files
        ]
        
        return MediaUploadStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=progress,
            uploaded_files=uploaded_files,
            failed_files=job.failed_files,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get upload status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
