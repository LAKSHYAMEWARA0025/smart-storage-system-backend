"""
Media Upload Celery Worker
Background task for processing media uploads
"""

from datetime import datetime
from typing import List, Dict, Any
from celery.signals import worker_process_init
from mongoengine import connect

from app.core.celery_app import celery_app
from app.models.mongo_models import MediaUploadJobModel
from app.services.media_handler import MediaHandler
from app.config import (
    MONGO_URI, 
    MONGO_DB_NAME, 
    SUPABASE_URL, 
    SUPABASE_KEY, 
    SUPABASE_SERVICE_KEY,
    SUPABASE_DB_URL
)


@worker_process_init.connect
def init_media_worker(**kwargs):
    """
    Initialize database connections when worker starts
    """
    print("🔧 Initializing media worker connections...")
    try:
        # Connect to MongoDB with MongoEngine
        connect(
            db=MONGO_DB_NAME,
            host=MONGO_URI,
            alias='default',
            uuidRepresentation='standard'
        )
        print("✅ Media worker MongoEngine connected")
        
        # Initialize Supabase clients
        from supabase import create_client
        import app.config as config
        
        config.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        config.supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Media worker Supabase connected")
        
    except Exception as e:
        print(f"❌ Media worker initialization failed: {e}")
        raise


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def process_media_upload_task(
    self,
    job_id: str,
    files_metadata: List[Dict[str, Any]],
    user_id: str
):
    """
    Process media upload in background
    
    Args:
        self: Celery task instance
        job_id: Job identifier
        files_metadata: List of dicts with {file_id, filename, content_type, size}
        user_id: User identifier
    """
    print(f"🚀 Starting media upload job: {job_id}")
    
    try:
        # Ensure Supabase is initialized
        from app.config import supabase_admin
        if supabase_admin is None:
            print("⚠️ Supabase not initialized, initializing now...")
            from supabase import create_client
            import app.config as config
            config.supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            print("✅ Supabase initialized in task")
        
        # Get job from database
        job = MediaUploadJobModel.objects(job_id=job_id).first()
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        # Update status to processing
        job.status = 'processing'
        job.progress_stage = 'uploading'
        job.updated_at = datetime.utcnow()
        job.save()
        
        # Initialize media handler and GridFS
        media_handler = MediaHandler()
        
        from app.config import get_mongodb_sync
        import gridfs
        from bson import ObjectId
        
        mongodb = get_mongodb_sync()
        fs = gridfs.GridFS(mongodb)
        
        uploaded_files = []
        failed_files = []
        
        # Process each file
        for idx, file_meta in enumerate(files_metadata):
            try:
                print(f"📤 Uploading file {idx + 1}/{len(files_metadata)}: {file_meta['filename']}")
                
                # Retrieve file from GridFS (sync)
                from pymongo import MongoClient
                sync_client = MongoClient(MONGO_URI)
                sync_db = sync_client[MONGO_DB_NAME]
                import gridfs as sync_gridfs
                sync_fs = sync_gridfs.GridFS(sync_db)
                
                grid_file = sync_fs.get(ObjectId(file_meta['file_id']))
                file_data = grid_file.read()
                
                print(f"📥 Retrieved from GridFS: {file_meta['filename']} ({len(file_data)} bytes)")
                
                # Generate storage path
                file_path = media_handler.generate_file_path(
                    user_id=user_id,
                    job_id=job_id,
                    filename=file_meta['filename']
                )
                
                # Upload to Supabase
                upload_result = media_handler.upload_to_supabase(
                    file_data=file_data,
                    file_path=file_path,
                    content_type=file_meta['content_type']
                )
                
                # Extract metadata
                metadata = media_handler.extract_metadata(
                    file_data=file_data,
                    filename=file_meta['filename'],
                    content_type=file_meta['content_type']
                )
                
                # Create record in files table
                from app.config import supabase_admin
                import hashlib
                
                file_hash = hashlib.sha256(file_data).hexdigest()
                extension = '.' + file_meta['filename'].split('.')[-1].lower() if '.' in file_meta['filename'] else ''
                
                # Determine file_type from category
                category = metadata.get('category', 'other')
                file_type = category.rstrip('s') if category.endswith('s') else category  # 'images' -> 'image'
                
                # Create record hash (hash of user_id + filename + file_hash)
                record_data = f"{user_id}{file_meta['filename']}{file_hash}"
                record_hash = hashlib.sha256(record_data.encode()).hexdigest()
                
                file_record = {
                    'user_id': user_id,
                    'filename': file_meta['filename'],
                    'url': upload_result['public_url'],
                    'file_type': file_type,
                    'extension': extension,
                    'file_hash': file_hash,
                    'file_size': file_meta['size'],
                    'category': category,
                    'metadata': metadata,
                    'record_hash': record_hash
                }
                
                supabase_admin.table('files').insert(file_record).execute()
                print(f"📝 Created file record in database")
                
                # Invalidate cache for file categories
                try:
                    from app.config import get_redis
                    import asyncio
                    
                    async def invalidate_cache():
                        redis = get_redis()
                        if redis:
                            await redis.delete(f"file_categories:{user_id}")
                            await redis.delete(f"files:{user_id}")
                            print(f"🗑️  Invalidated cache for user: {user_id}")
                    
                    asyncio.run(invalidate_cache())
                except Exception as cache_error:
                    print(f"⚠️  Could not invalidate cache: {cache_error}")
                
                # Track successful upload
                uploaded_files.append({
                    'filename': file_meta['filename'],
                    'url': upload_result['storage_url'],
                    'public_url': upload_result['public_url'],
                    'size_bytes': file_meta['size'],
                    'content_type': file_meta['content_type'],
                    'metadata': metadata
                })
                
                # Delete from GridFS after successful upload
                sync_fs.delete(ObjectId(file_meta['file_id']))
                print(f"🗑️  Cleaned up GridFS: {file_meta['filename']}")
                
                print(f"✅ Successfully uploaded: {file_meta['filename']}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Failed to upload {file_meta['filename']}: {error_msg}")
                
                failed_files.append({
                    'filename': file_meta['filename'],
                    'error': error_msg
                })
            
            # Update progress after each file
            job.progress_current = idx + 1
            job.progress_percentage = ((idx + 1) / len(files_metadata)) * 100
            job.uploaded_files = uploaded_files
            job.failed_files = failed_files
            job.updated_at = datetime.utcnow()
            job.save()
        
        # Update final status
        if failed_files and uploaded_files:
            job.status = 'completed_with_errors'
        elif failed_files and not uploaded_files:
            job.status = 'failed'
            job.error_message = f"All {len(failed_files)} files failed to upload"
        else:
            job.status = 'completed'
        
        job.progress_stage = 'completed'
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.save()
        
        print(f"🎉 Media upload job completed: {job_id}")
        print(f"   Uploaded: {len(uploaded_files)}, Failed: {len(failed_files)}")
        
        return {
            'job_id': job_id,
            'status': job.status,
            'uploaded': len(uploaded_files),
            'failed': len(failed_files)
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"💥 Media upload job failed: {job_id} - {error_msg}")
        
        # Clean up GridFS files
        try:
            from app.config import get_mongodb_sync
            import gridfs
            from bson import ObjectId
            
            mongodb = get_mongodb_sync()
            fs = gridfs.GridFS(mongodb)
            
            for file_meta in files_metadata:
                try:
                    fs.delete(ObjectId(file_meta['file_id']))
                    print(f"🗑️  Cleaned up GridFS: {file_meta['filename']}")
                except Exception as cleanup_error:
                    print(f"⚠️ Could not cleanup GridFS file: {cleanup_error}")
        except Exception as cleanup_error:
            print(f"⚠️ GridFS cleanup failed: {cleanup_error}")
        
        # Update job status to failed
        try:
            job = MediaUploadJobModel.objects(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = error_msg
                job.updated_at = datetime.utcnow()
                job.completed_at = datetime.utcnow()
                job.save()
        except Exception as update_error:
            print(f"⚠️ Could not update job status: {update_error}")
        
        # Re-raise for Celery retry logic
        raise
