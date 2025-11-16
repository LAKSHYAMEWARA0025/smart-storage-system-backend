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

# Import our new security function
from app.security import get_current_user

router = APIRouter()
BUCKET_NAME = "uploads"
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
async def media_storage_function(user_id: UUID, file_content: bytes, filename: str) -> dict:
    """
    This is our original function for uploading files to Supabase
    Storage and saving metadata to the 'files' table.
    It also invalidates the cache.
    """
    print(f"--- Media Storage Function CALLED for user: {user_id} ---")
    try:
        supabase, redis_client = get_clients()
        
        file_details = get_file_details(filename)
        file_path_in_bucket = f"{user_id}/{filename}"
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"
        
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=file_content,
            file_options={"content-type": content_type}
        )
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path_in_bucket)
        
        new_file_data = FileBase(
            user_id=str(user_id), # <-- This is our fix from before
            filename=filename,
            url=public_url,
            file_type=file_details["file_type"],
            extension=file_details["extension"]
        )
        
        db_res = supabase.table("files").insert(
            new_file_data.model_dump(),
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
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Classifies an incoming file and routes it to the correct handler.
    """
    
    file_content = await file.read()
    file_details = get_file_details(file.filename)
    extension = file_details["extension"]

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
            filename=file.filename
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