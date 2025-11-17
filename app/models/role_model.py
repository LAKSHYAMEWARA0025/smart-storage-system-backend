"""
Role Models
Defines user roles and profile models
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional


class UserRole(str, Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class UserProfile(BaseModel):
    """User profile with role information"""
    id: str
    role: UserRole
    created_at: str
    updated_at: str


class UserWithRole(BaseModel):
    """User data with role"""
    user_id: str
    email: str
    role: UserRole
