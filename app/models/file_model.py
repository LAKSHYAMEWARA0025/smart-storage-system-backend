from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID  # <-- Keep this import

class FileBase(BaseModel):
    # --- CHANGE THIS ---
    # From: user_id: UUID
    # To:   user_id: str
    user_id: str = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    # -------------------
    filename: str = Field(..., example="my_vacation_video.mp4")
    url: str = Field(..., example="https://xyz.supabase.co/storage/v1/...")
    file_type: str = Field(..., example="video")
    extension: str = Field(..., example=".mp4")

class FileResponse(FileBase):
    id: int = Field(..., example=1)
    
    class Config:
        from_attributes = True