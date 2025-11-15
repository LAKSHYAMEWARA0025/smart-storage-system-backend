from pydantic import BaseModel, Field
from typing import Optional
# from uuid import UUID, uuid4 # We'll use UUID for user_id

# This is the base model. It defines the core data.
class FileBase(BaseModel):
    # We'll assume user_id is a UUID (Universally Unique Identifier)
    # This is much better practice than a simple string.
    user_id: str = Field(..., example="test-user")
    filename: str = Field(..., example="my_vacation_video.mp4")
    url: str = Field(..., example="https://xyz.supabase.co/storage/v1/...")
    file_type: str = Field(..., example="video")
    extension: str = Field(..., example=".mp4")

# This model will be used when returning data from the API
# It includes the 'id' that Supabase will create for us.
class FileResponse(FileBase):
    id: int = Field(..., example="a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890")
    
    # This tells Pydantic it's okay to read data from 
    # a database object (not just a dict).
    class Config:
        # orm_mode = True
        from_attributes = True