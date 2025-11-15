import mimetypes
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.encoders import jsonable_encoder
from typing import List, Any

# Import our Supabase client
from app.config import supabase

# Import our helper and models
from app.utils.file_helpers import get_file_details
from app.models.file_model import FileBase, FileResponse

router = APIRouter()
BUCKET_NAME = "uploads"


# ===================================================================
#  1. THE NEW JSON STORAGE FUNCTION (Placeholder)
# ===================================================================
async def json_storage_function(user_id: str, file_content: bytes, filename: str) -> dict:
    """
    This is the new function for handling JSON data.
    We will build this out later.
    """
    print(f"--- JSON Storage Function CALLED for user: {user_id} ---")
    
    # For now, just parse it to make sure it's valid JSON
    try:
        data = json.loads(file_content.decode('utf-8'))
        print("File was valid JSON.")
        
        # ---
        # TODO: Add logic here to save the JSON data to a different table
        # ---
        
        return {"message": "JSON data processed successfully", "filename": filename}
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON content.")
        raise HTTPException(status_code=400, detail="Invalid JSON content in file.")


# ===================================================================
#  2. THE MEDIA STORAGE FUNCTION (Our Old Logic)
# ===================================================================
async def media_storage_function(user_id: str, file_content: bytes, filename: str) -> dict:
    """
    This is our original function for uploading files to Supabase
    Storage and saving metadata to the 'files' table.
    """
    print(f"--- Media Storage Function CALLED for user: {user_id} ---")
    try:
        # 1. Get file details
        file_details = get_file_details(filename)
        
        # 2. Create path
        file_path_in_bucket = f"{user_id}/{filename}"

        # 3. Guess content-type
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        # 4. Upload to Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=file_content,
            file_options={"content-type": content_type}
        )

        # 5. Get public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
            file_path_in_bucket
        )
        
        # 6. Prepare data for DB
        new_file_data = FileBase(
            user_id=user_id,
            filename=filename,
            url=public_url,
            file_type=file_details["file_type"],
            extension=file_details["extension"]
        )

        # 7. Save to DB
        db_res = supabase.table("files").insert(
            new_file_data.model_dump()
        ).execute()

        if not db_res.data:
            raise HTTPException(status_code=500, detail="Failed to save file metadata.")

        # 8. Return the new record
        validated_data = FileResponse.model_validate(db_res.data[0])
        return jsonable_encoder(validated_data)

    except Exception as e:
        print(f"Error during media upload: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
#  3. THE MAIN UPLOAD ROUTE (The Classifier)
# ===================================================================
@router.post("/upload")  # Response model is removed since it can return 2 types
async def upload_file(
    user_id: str = Form(...),
    is_json_content: bool = Form(False),  # Your boolean flag
    file: UploadFile = File(...)
):
    """
    Classifies an incoming file and routes it to the correct handler.
    - If it's a .json file OR
    - If it's a .txt file AND is_json_content is True
    ...it goes to the JSON handler.
    
    Otherwise, it goes to the media storage handler.
    """
    
    # Read the file content one time
    file_content = await file.read()
    
    # Get the file extension
    file_details = get_file_details(file.filename)
    extension = file_details["extension"]

    # --- THIS IS YOUR CLASSIFIER LOGIC ---
    if extension == '.json' or (extension == '.txt' and is_json_content):
        # Call the JSON function
        return await json_storage_function(
            user_id=user_id,
            file_content=file_content,
            filename=file.filename
        )
    else:
        # Call the Media function
        return await media_storage_function(
            user_id=user_id,
            file_content=file_content,
            filename=file.filename
        )


# ===================================================================
#  4. THE GET ROUTES (Unchanged)
# ===================================================================

@router.get("/files", response_model=List[FileResponse])
async def get_files_for_user(user_id: str):
    """
    Retrieves all file records for a specific user.
    """
    try:
        res = supabase.table("files").select("*").eq("user_id", user_id).execute()
        validated_data = [FileResponse.model_validate(item) for item in res.data]
        return jsonable_encoder(validated_data)
    except Exception as e:
        print(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch files.")


@router.get("/files/search", response_model=List[FileResponse])
async def search_files_by_type(user_id: str, file_type: str):
    """
    Retrieves files for a user, filtered by file_type (e.g., 'image', 'video').
    """
    try:
        res = supabase.table("files").select("*") \
            .eq("user_id", user_id) \
            .eq("file_type", file_type.lower()) \
            .execute()
        validated_data = [FileResponse.model_validate(item) for item in res.data]
        return jsonable_encoder(validated_data)
    except Exception as e:
        print(f"Error searching files: {e}")
        raise HTTPException(status_code=500, detail="Could not search files.")