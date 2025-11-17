"""
Media Handler Service
Handles media file uploads to Supabase Storage
"""

from typing import Dict, Any, Optional
from io import BytesIO
from app.config import SUPABASE_BUCKET_NAME
from app.utils.media_metadata import extract_image_metadata, get_file_category


class MediaHandler:
    """
    Service for handling media file uploads and metadata extraction
    """
    
    def __init__(self):
        self.bucket_name = SUPABASE_BUCKET_NAME
    
    def upload_to_supabase(
        self,
        file_data: bytes,
        file_path: str,
        content_type: str
    ) -> Dict[str, str]:
        """
        Upload file directly to Supabase Storage
        
        Args:
            file_data: File bytes
            file_path: Path in bucket (e.g., "user_id/job_id/filename.jpg")
            content_type: MIME type
            
        Returns:
            Dictionary with storage_url and public_url
        """
        try:
            # Get Supabase client from config (initialized in worker)
            from app.config import supabase_admin
            
            if supabase_admin is None:
                raise Exception("Supabase client not initialized. Make sure worker is properly started.")
            
            # Upload to Supabase Storage
            response = supabase_admin.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    'content-type': content_type,
                    'cache-control': '3600',
                    'upsert': 'false'  # Don't overwrite existing files
                }
            )
            
            # Get public URL
            public_url = supabase_admin.storage.from_(self.bucket_name).get_public_url(file_path)
            
            print(f"✅ Uploaded to Supabase: {file_path}")
            
            return {
                'storage_url': f"{self.bucket_name}/{file_path}",
                'public_url': public_url
            }
            
        except Exception as e:
            print(f"❌ Failed to upload to Supabase: {e}")
            raise Exception(f"Supabase upload failed: {str(e)}")
    
    def extract_metadata(
        self,
        file_data: bytes,
        filename: str,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from file based on type
        
        Args:
            file_data: File bytes
            filename: Original filename
            content_type: MIME type
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'size_bytes': len(file_data),
            'content_type': content_type
        }
        
        try:
            # Get file extension
            extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
            category = get_file_category(extension)
            metadata['category'] = category
            
            # Extract type-specific metadata
            if category == 'images' and content_type.startswith('image/'):
                image_meta = extract_image_metadata(file_data, filename)
                metadata.update(image_meta)
            
            # For videos, we'd need temp file - skip for now or implement later
            # elif category == 'videos' and content_type.startswith('video/'):
            #     video_meta = extract_video_metadata(temp_path)
            #     metadata.update(video_meta)
            
        except Exception as e:
            print(f"⚠️ Could not extract metadata: {e}")
            metadata['metadata_error'] = str(e)
        
        return metadata
    
    def validate_file(
        self,
        filename: str,
        size: int,
        content_type: str,
        max_size_mb: int = 50,
        allowed_types: Optional[list] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate file before upload
        
        Args:
            filename: Original filename
            size: File size in bytes
            content_type: MIME type
            max_size_mb: Maximum file size in MB
            allowed_types: List of allowed MIME types
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if size > max_size_bytes:
            return False, f"File size ({size / 1024 / 1024:.2f}MB) exceeds maximum ({max_size_mb}MB)"
        
        # Check file type
        if allowed_types and content_type not in allowed_types:
            return False, f"File type '{content_type}' not allowed"
        
        # Check filename
        if not filename or len(filename) > 255:
            return False, "Invalid filename"
        
        return True, None
    
    def generate_file_path(
        self,
        user_id: str,
        job_id: str,
        filename: str
    ) -> str:
        """
        Generate storage path for file
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            filename: Original filename
            
        Returns:
            Storage path
        """
        import re
        import unicodedata
        
        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)
        
        # Remove non-ASCII characters
        filename = filename.encode('ascii', 'ignore').decode('ascii')
        
        # Replace spaces and special characters with underscores
        filename = re.sub(r'[^\w\s.-]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        
        # Remove multiple consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Ensure filename is not empty
        if not filename or filename == '_':
            filename = 'file'
        
        # Create path: user_id/job_id/filename
        return f"{user_id}/{job_id}/{filename}"
