import mimetypes
import json  # <-- Added for caching
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.encoders import jsonable_encoder
from typing import List, Any
from uuid import UUID

# Import our Supabase client AND our new Redis client
from app.config import get_supabase, get_redis 

# Import our helper and models
from app.utils.file_helpers import get_file_details
from app.models.file_model import FileBase, FileResponse

# Import our new security functions
from app.security import get_current_user, get_current_user_with_role, require_admin

from app.config import SUPABASE_BUCKET_NAME

router = APIRouter()
BUCKET_NAME = SUPABASE_BUCKET_NAME
CACHE_EXPIRATION_SECONDS = 3600 # Cache for 1 hour

# Get clients
supabase = None
redis_client = None

def get_clients():
    """Get supabase and redis clients"""
    global supabase, redis_client
    if supabase is None:
        supabase = get_supabase()
    if redis_client is None:
        redis_client = get_redis()
    return supabase, redis_client


def get_admin_client():
    """Get supabase admin client"""
    from app.config import get_supabase_admin
    return get_supabase_admin()


# ===================================================================
#  1. THE JSON STORAGE FUNCTION (Integrated with Smart Storage)
# ===================================================================
async def json_storage_function(user_id: UUID, file_content: bytes, filename: str) -> dict:
    """
    Routes JSON files to the smart storage system for structured data handling.
    """
    print(f"--- JSON Storage Function CALLED for user: {user_id} ---")
    try:
        # Validate JSON
        data = json.loads(file_content.decode('utf-8'))
        print("File was valid JSON.")
        
        # Route to smart storage system
        from app.controllers.upload_controller import UploadController
        from fastapi import UploadFile
        from io import BytesIO
        
        # Create UploadFile object from bytes
        file_obj = BytesIO(file_content)
        upload_file = UploadFile(filename=filename, file=file_obj)
        
        # Analyze the file
        analysis_result = await UploadController.analyze_upload(
            files=[upload_file],
            user_id=str(user_id),
            metadata=None
        )
        
        # If no conflicts, auto-execute
        if not analysis_result['requires_decision']:
            # Auto-execute with default decisions
            decisions = {}
            for schema in analysis_result['schemas_detected']:
                decisions[schema['schema_id']] = {
                    'action': 'create',
                    'custom_name': None
                }
            
            execute_result = await UploadController.execute_upload(
                analysis_id=analysis_result['analysis_id'],
                decisions=decisions,
                user_id=str(user_id)
            )
            
            response_data = {
                "message": "JSON data processed and stored successfully",
                "filename": filename,
                "job_id": execute_result['job_id'],
                "schemas_detected": len(analysis_result['schemas_detected']),
                "total_records": analysis_result['total_records']
            }
        else:
            # Conflicts detected - return analysis for user decision
            response_data = {
                "message": "JSON data analyzed - user decision required",
                "filename": filename,
                "analysis_id": analysis_result['analysis_id'],
                "requires_decision": True,
                "conflicts": [
                    s['conflict'] for s in analysis_result['schemas_detected']
                    if s.get('conflict')
                ]
            }
        
        # --- CACHE INVALIDATION ---
        try:
            cache_key_files = f"files:{user_id}"
            await redis_client.delete(cache_key_files)
            print(f"Cache invalidated for key: {cache_key_files}")
        except Exception as e:
            print(f"Redis cache invalidation failed: {e}")
        # --------------------------
        
        return jsonable_encoder(response_data)
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON content.")
        raise HTTPException(status_code=400, detail="Invalid JSON content in file.")
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process JSON file: {str(e)}")


# ===================================================================
#  2. THE MEDIA STORAGE FUNCTION (with Cache Invalidation)
# ===================================================================
async def media_storage_function(
    user_id: UUID, 
    file_content: bytes, 
    filename: str,
    tags: List[str] = None,
    description: str = None
) -> dict:
    """
    Upload files to Supabase Storage with enhanced metadata extraction.
    Includes deduplication, dimensions (images), duration (videos), etc.
    """
    print(f"--- Media Storage Function CALLED for user: {user_id} ---")
    try:
        from app.config import get_supabase_admin
        supabase, redis_client = get_clients()
        supabase_admin = get_supabase_admin()
        from app.utils.media_metadata import build_enhanced_metadata, calculate_file_hash
        from app.utils.filename_sanitizer import sanitize_filename, generate_unique_filename
        import tempfile
        import os
        
        file_details = get_file_details(filename)
        extension = file_details["extension"]
        
        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(file_content)
        
        # Sanitize filename for storage (keep original for metadata)
        original_filename = filename
        sanitized_filename = generate_unique_filename(filename, file_hash)
        
        # Check if file already exists (deduplication) - use admin client
        existing_file = supabase_admin.table("files").select("*").eq("user_id", str(user_id)).eq("file_hash", file_hash).execute()
        
        if existing_file.data:
            print(f"✅ File already exists (hash: {file_hash[:8]}...), returning existing URL")
            return jsonable_encoder(existing_file.data[0])
        
        # For videos, save to temp file for ffmpeg processing
        temp_file_path = None
        if file_details["file_type"] == "video":
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
        
        # Extract enhanced metadata (use original filename for metadata)
        enhanced_metadata = build_enhanced_metadata(
            file_content=file_content,
            filename=original_filename,
            extension=extension,
            tags=tags,
            description=description,
            temp_file_path=temp_file_path
        )
        
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        # Upload to Supabase Storage using sanitized filename
        file_path_in_bucket = f"{user_id}/{sanitized_filename}"
        content_type, _ = mimetypes.guess_type(original_filename)
        content_type = content_type or "application/octet-stream"
        
        print(f"📁 Original filename: {original_filename}")
        print(f"📁 Sanitized filename: {sanitized_filename}")
        print(f"📁 Storage path: {file_path_in_bucket}")
        
        # Supabase storage upload (metadata stored in database, not storage)
        # Use admin client to bypass storage RLS policies
        supabase_admin.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=file_content,
            file_options={"content-type": content_type}
        )
        public_url = supabase_admin.storage.from_(BUCKET_NAME).get_public_url(file_path_in_bucket)
        
        # Prepare file data with enhanced metadata
        # Store original filename in metadata, use sanitized for storage
        new_file_data = {
            "user_id": str(user_id),
            "filename": sanitized_filename,  # Sanitized filename for storage
            "url": public_url,
            "file_type": file_details["file_type"],
            "extension": file_details["extension"],
            "file_hash": enhanced_metadata["file_hash"],
            "file_size": enhanced_metadata["file_size"],
            "category": enhanced_metadata["category"],
            "metadata": {
                **enhanced_metadata,
                "original_filename": original_filename  # Preserve original filename
            }
        }
        
        # Insert into database using admin client to bypass RLS
        db_res = supabase_admin.table("files").insert(
            new_file_data,
            returning="minimal"
        ).execute()

        # --- CACHE INVALIDATION ---
        try:
            cache_key_files = f"files:{user_id}"
            await redis_client.delete(cache_key_files)
            print(f"Cache invalidated for key: {cache_key_files}")
        except Exception as e:
            print(f"Redis cache invalidation failed: {e}")
        # --------------------------
        
        return jsonable_encoder(new_file_data)
        
    except Exception as e:
        print(f"Error during media upload: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
#  3. THE MAIN UPLOAD ROUTE (Unchanged)
# ===================================================================
@router.post("/upload")
async def upload_file(
    is_json_content: bool = Form(False),
    file: UploadFile = File(...),
    tags: str = Form(None),  # Comma-separated tags
    description: str = Form(None),
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Classifies an incoming file and routes it to the correct handler.
    Supports optional tags and description for media files.
    """
    
    file_content = await file.read()
    file_details = get_file_details(file.filename)
    extension = file_details["extension"]
    
    # Parse tags if provided
    tags_list = [tag.strip() for tag in tags.split(',')] if tags else []

    if extension == '.json' or (extension == '.txt' and is_json_content):
        return await json_storage_function(
            user_id=current_user_id,
            file_content=file_content,
            filename=file.filename
        )
    else:
        return await media_storage_function(
            user_id=current_user_id,
            file_content=file_content,
            filename=file.filename,
            tags=tags_list,
            description=description
        )


# ===================================================================
#  4. THE GET ROUTES (with Caching)
# ===================================================================

@router.get("/files", response_model=List[FileResponse])
async def get_files_for_user(
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Retrieves all file records for the authenticated user.
    Checks cache first.
    """
    supabase, redis_client = get_clients()
    
    # 1. Define a unique cache key for this user's request
    cache_key = f"files:{current_user_id}"
    
    try:
        # 2. Check Redis first
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            print(f"--- CACHE HIT for key: {cache_key} ---")
            # Data is stored as a JSON string, so we parse it
            return json.loads(cached_data)

        # 3. CACHE MISS: If no data, query the database
        print(f"--- CACHE MISS for key: {cache_key} ---")
        res = supabase.table("files").select("*").eq("user_id", str(current_user_id)).execute()
        
        # 4. Prepare data for response and cache
        response_data = jsonable_encoder(res.data)
        
        # 5. Store in Redis (as a JSON string) with an expiration
        await redis_client.setex(
            cache_key,
            CACHE_EXPIRATION_SECONDS,
            json.dumps(response_data)
        )
        
        return response_data
        
    except Exception as e:
        print(f"Error fetching files (with cache): {e}")
        # Robustness: If cache fails, just hit the DB
        try:
            print("--- Cache failed, falling back to DB ---")
            res = supabase.table("files").select("*").eq("user_id", str(current_user_id)).execute()
            return jsonable_encoder(res.data)
        except Exception as db_e:
            print(f"DB fallback also failed: {db_e}")
            raise HTTPException(status_code=500, detail="Could not fetch files from DB or cache.")


@router.get("/files/search", response_model=List[FileResponse])
async def search_files_by_type(
    file_type: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Retrieves files for the authenticated user, filtered by file_type.
    Checks cache first.
    """
    supabase, redis_client = get_clients()
    
    # 1. Define a unique cache key for this specific search
    cache_key = f"files_search:{current_user_id}:{file_type.lower()}"
    
    try:
        # 2. Check Redis
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            print(f"--- CACHE HIT for key: {cache_key} ---")
            return json.loads(cached_data)

        # 3. CACHE MISS: Query the database
        print(f"--- CACHE MISS for key: {cache_key} ---")
        res = supabase.table("files").select("*") \
            .eq("user_id", str(current_user_id)) \
            .eq("file_type", file_type.lower()) \
            .execute()
            
        # 4. Prepare data
        response_data = jsonable_encoder(res.data)
        
        # 5. Store in Redis
        await redis_client.setex(
            cache_key,
            CACHE_EXPIRATION_SECONDS,
            json.dumps(response_data)
        )
        
        return response_data
        
    except Exception as e:
        print(f"Error searching files (with cache): {e}")
        # Robustness: If cache fails, just hit the DB
        try:
            print("--- Cache failed, falling back to DB ---")
            res = supabase.table("files").select("*") \
                .eq("user_id", str(current_user_id)) \
                .eq("file_type", file_type.lower()) \
                .execute()
            return jsonable_encoder(res.data)
        except Exception as db_e:
            print(f"DB fallback also failed: {db_e}")
            raise HTTPException(status_code=500, detail="Could not search files from DB or cache.")


@router.get("/files/categories")
async def get_file_categories(
    refresh: bool = False,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get all file categories with counts and extensions for the authenticated user.
    Returns categorized summary of user's files.
    
    Args:
        refresh: Set to true to bypass cache and get fresh data
    """
    # Use admin client to bypass RLS
    supabase = get_admin_client()
    redis_client = get_redis()
    
    cache_key = f"file_categories:{current_user_id}"
    
    try:
        # Check cache (unless refresh is requested)
        if not refresh:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                print(f"--- CACHE HIT for key: {cache_key} ---")
                return json.loads(cached_data)
        else:
            print(f"--- CACHE REFRESH requested for key: {cache_key} ---")
        
        # Fetch all user files
        print(f"--- CACHE MISS for key: {cache_key} ---")
        print(f"--- Querying for user_id: {current_user_id} (type: {type(current_user_id)}) ---")
        
        res = supabase.table("files").select("extension, category").eq("user_id", str(current_user_id)).execute()
        
        print(f"--- Query returned {len(res.data)} records ---")
        if len(res.data) > 0:
            print(f"--- Sample record: {res.data[0]} ---")
        
        # Aggregate by category
        categories_map = {}
        for file in res.data:
            category = file.get('category', 'other')
            extension = file.get('extension', '')
            
            if category not in categories_map:
                categories_map[category] = {
                    'name': category,
                    'count': 0,
                    'extensions': set()
                }
            
            categories_map[category]['count'] += 1
            if extension:
                categories_map[category]['extensions'].add(extension)
        
        # Convert to list and make extensions a list
        categories_list = [
            {
                'name': cat['name'],
                'count': cat['count'],
                'extensions': sorted(list(cat['extensions']))
            }
            for cat in categories_map.values()
        ]
        
        response_data = {'categories': categories_list}
        
        # Cache the result
        await redis_client.setex(
            cache_key,
            CACHE_EXPIRATION_SECONDS,
            json.dumps(response_data)
        )
        
        return response_data
        
    except Exception as e:
        print(f"Error fetching file categories: {e}")
        raise HTTPException(status_code=500, detail=f"Could not fetch file categories: {str(e)}")


@router.get("/files/by-category")
async def get_files_by_categories(
    categories: str,  # Comma-separated list: "images,videos"
    refresh: bool = False,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Get files filtered by one or more categories.
    
    Args:
        categories: Comma-separated category names (e.g., "images,videos,documents")
        refresh: Set to true to bypass cache and get fresh data
    
    Returns:
        List of files matching the specified categories with full metadata
    """
    # Use admin client to bypass RLS
    supabase = get_admin_client()
    redis_client = get_redis()
    
    # Parse categories
    category_list = [cat.strip().lower() for cat in categories.split(',')]
    cache_key = f"files_by_category:{current_user_id}:{':'.join(sorted(category_list))}"
    
    try:
        # Check cache (unless refresh is requested)
        if not refresh:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                print(f"--- CACHE HIT for key: {cache_key} ---")
                return json.loads(cached_data)
        else:
            print(f"--- CACHE REFRESH requested for key: {cache_key} ---")
        
        # Fetch files matching categories
        print(f"--- CACHE MISS for key: {cache_key} ---")
        res = supabase.table("files").select("*").eq("user_id", str(current_user_id)).in_("category", category_list).execute()
        
        response_data = {
            'total': len(res.data),
            'categories': category_list,
            'files': jsonable_encoder(res.data)
        }
        
        # Cache the result
        await redis_client.setex(
            cache_key,
            CACHE_EXPIRATION_SECONDS,
            json.dumps(response_data)
        )
        
        return response_data
        
    except Exception as e:
        print(f"Error fetching files by category: {e}")
        raise HTTPException(status_code=500, detail=f"Could not fetch files by category: {str(e)}")



# ===================================================================
#  ADMIN ENDPOINTS (Role-based access)
# ===================================================================

@router.get("/admin/files/all")
async def get_all_files_admin(admin: dict = Depends(require_admin)):
    """
    Admin-only endpoint to get all files from all users.
    Demonstrates role-based access control.
    """
    try:
        supabase = get_admin_client()
        
        # Admin can see all files
        res = supabase.table("files").select("*").order("created_at", desc=True).limit(100).execute()
        
        return {
            "total": len(res.data),
            "admin_user": admin["email"],
            "files": jsonable_encoder(res.data)
        }
        
    except Exception as e:
        print(f"Error fetching all files (admin): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/stats")
async def get_storage_stats(admin: dict = Depends(require_admin)):
    """
    Admin-only endpoint to get storage statistics.
    """
    try:
        supabase = get_admin_client()
        
        # Get total files count
        files_res = supabase.table("files").select("id", count="exact").execute()
        total_files = files_res.count
        
        # Get total storage used
        size_res = supabase.table("files").select("file_size").execute()
        total_size = sum(file.get("file_size", 0) or 0 for file in size_res.data)
        
        # Get files by category
        category_res = supabase.table("files").select("category").execute()
        categories = {}
        for file in category_res.data:
            cat = file.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files_by_category": categories,
            "admin_user": admin["email"]
        }
        
    except Exception as e:
        print(f"Error fetching storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
