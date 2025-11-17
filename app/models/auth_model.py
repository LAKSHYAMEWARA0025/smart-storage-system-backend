from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserAuth(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: Optional[str] = None
    message: Optional[str] = None

class UpdateRoleRequest(BaseModel):
    new_role: str = Field(..., description="New role: user, admin, or moderator")