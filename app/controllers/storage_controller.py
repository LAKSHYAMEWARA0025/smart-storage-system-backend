import mimetypes
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List
from uuid import UUID

# Import our Supabase client
from app.config import supabase

# Import our helper and models
from app.utils.file_helpers import get_file_details
from app.models.file_model import FileBase, FileResponse

# Create a new router
router = APIRouter()

# Name of your Supabase Storage bucket
BUCKET_NAME = "uploads"


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    user_id: str = Form(...), 
    file: UploadFile = File(...)
):
    """
    Endpoint to upload a file to Supabase Storage and save its
    metadata to the PostgreSQL database.
    """
    try:
        # 1. Read the file's content
        file_content = await file.read()
        
        # 2. Get file details (extension, file_type)
        file_details = get_file_details(file.filename)
        
        # 3. Create a unique path for the file in storage
        # We'll store it as: public/user_id/filename
        file_path_in_bucket = f"{user_id}/{file.filename}"

        # 4. Upload to Supabase Storage
        # We must detect the content-type (e.g., 'image/png')
        content_type, _ = mimetypes.guess_type(file.filename)
        content_type = content_type or "application/octet-stream"

        upload_res = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=file_content,
            file_options={"content-type": content_type}
        )

        # 5. Get the public URL
        url_res = supabase.storage.from_(BUCKET_NAME).get_public_url(
            file_path_in_bucket
        )
        public_url = url_res
        
        # 6. Prepare data for the database
        new_file_data = FileBase(
            user_id=user_id,
            filename=file.filename,
            url=public_url,
            file_type=file_details["file_type"],
            extension=file_details["extension"]
        )

        # 7. Save the metadata to the 'files' table in PostgreSQL
        db_res = supabase.table("files").insert(
            new_file_data.model_dump() # Use .model_dump() for Pydantic v2
        ).execute()

        if not db_res.data:
            raise HTTPException(status_code=500, detail="Failed to save file metadata to database.")

        # Return the newly created database record
        # db_res.data[0] contains the new row
        # return db_res.data[0]
        # NEW
        return FileResponse.model_validate(db_res.data[0])

    except Exception as e:
        print(f"Error during upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=List[FileResponse])
async def get_files_for_user(user_id: str):
    """
    Retrieves all file records for a specific user.
    """
    try:
        res = supabase.table("files").select("*").eq("user_id", str(user_id)).execute()
        # return res.data
        # NEW
        return [FileResponse.model_validate(item) for item in res.data]
    except Exception as e:
        print(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch files.")


@router.get("/files/search", response_model=List[FileResponse])
async def search_files_by_type(user_id: str, file_type: str):
    """
    Retrieves files for a user, filtered by file_type (e.g., 'image', 'video').
    This is your "virtual folder" endpoint.
    """
    try:
        res = supabase.table("files").select("*") \
            .eq("user_id", str(user_id)) \
            .eq("file_type", file_type.lower()) \
            .execute()
        # return res.data
        return [FileResponse.model_validate(item) for item in res.data]
    except Exception as e:
        print(f"Error searching files: {e}")
        raise HTTPException(status_code=500, detail="Could not search files.")