import mimetypes
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.encoders import jsonable_encoder
from typing import List, Any
from uuid import UUID

# Import our Supabase client
from app.config import supabase

# Import our helper and models
from app.utils.file_helpers import get_file_details
from app.models.file_model import FileBase, FileResponse

# Import our new security function
from app.security import get_current_user

router = APIRouter()
BUCKET_NAME = "uploads"


# ===================================================================
#  1. THE JSON STORAGE FUNCTION
# ===================================================================
async def json_storage_function(user_id: UUID, file_content: bytes, filename: str) -> dict:
    """
    This is the new function for handling JSON data.
    """
    print(f"--- JSON Storage Function CALLED for user: {user_id} ---")
    try:
        data = json.loads(file_content.decode('utf-8'))
        print("File was valid JSON.")
        
        response_data = {"message": "JSON data processed successfully", "filename": filename}
        # Wrap in encoder to be 100% safe
        return jsonable_encoder(response_data)
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON content.")
        raise HTTPException(status_code=400, detail="Invalid JSON content in file.")


# ===================================================================
#  2. THE MEDIA STORAGE FUNCTION (The Final Fix)
# ===================================================================
async def media_storage_function(user_id: UUID, file_content: bytes, filename: str) -> dict:
    """
    This is our original function for uploading files to Supabase
    Storage and saving metadata to the 'files' table.
    """
    print(f"--- Media Storage Function CALLED for user: {user_id} ---")
    try:
        file_details = get_file_details(filename)
        # We can use the UUID object for the path, that's fine
        file_path_in_bucket = f"{user_id}/{filename}"
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"
        
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=file_content,
            file_options={"content-type": content_type}
        )
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path_in_bucket)
        
        # --- THIS IS THE FIX ---
        # Convert the UUID to a string *before* creating the Pydantic model
        new_file_data = FileBase(
            user_id=str(user_id), # <-- CONVERT UUID TO STRING
            filename=filename,
            url=public_url,
            file_type=file_details["file_type"],
            extension=file_details["extension"]
        )
        # -----------------------
        
        db_res = supabase.table("files").insert(
            new_file_data.model_dump(),
            returning="minimal"
        ).execute()
        
        # Now we are returning a model that *only* contains strings,
        # so the encoder will have no problem.
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
    The user is authenticated via a JWT Bearer Token.
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
#  4. THE GET ROUTES (Unchanged, but correct)
# ===================================================================

@router.get("/files", response_model=List[FileResponse])
async def get_files_for_user(
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Retrieves all file records for the authenticated user.
    """
    try:
        # str(current_user_id) is correct for the query
        res = supabase.table("files").select("*").eq("user_id", str(current_user_id)).execute()
        
        # jsonable_encoder is correct here, it handles the list of dicts
        return jsonable_encoder(res.data)
        
    except Exception as e:
        print(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch files.")


@router.get("/files/search", response_model=List[FileResponse])
async def search_files_by_type(
    file_type: str,
    current_user_id: UUID = Depends(get_current_user)
):
    """
    Retrieves files for the authenticated user, filtered by file_type.
    """
    try:
        res = supabase.table("files").select("*") \
            .eq("user_id", str(current_user_id)) \
            .eq("file_type", file_type.lower()) \
            .execute()
            
        # jsonable_encoder is correct here
        return jsonable_encoder(res.data)
        
    except Exception as e:
        print(f"Error searching files: {e}")
        raise HTTPException(status_code=500, detail="Could not search files.")