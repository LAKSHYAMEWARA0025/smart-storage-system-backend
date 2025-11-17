from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import get_supabase
from app.models.role_model import UserRole
from typing import Dict

oauth2_scheme = HTTPBearer()


def get_current_user(auth: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """
    Dependency that verifies the JWT and returns the user's ID.
    This will be run on every protected endpoint.
    """
    token = auth.credentials 
    
    try:
        supabase = get_supabase()
        res = supabase.auth.get_user(token)
        
        if not res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return res.user.id
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_role(auth: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> Dict:
    """
    Get current user with role information from user_profiles table.
    Returns dict with user_id, email, and role.
    """
    token = auth.credentials
    
    try:
        from app.config import get_supabase_admin
        
        supabase = get_supabase()
        supabase_admin = get_supabase_admin()
        
        user_res = supabase.auth.get_user(token)
        
        if not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user role from user_profiles table using admin client (bypasses RLS)
        profile_res = supabase_admin.table("user_profiles").select("role").eq("id", user_res.user.id).execute()
        
        role = "user"  # Default role
        if profile_res.data and len(profile_res.data) > 0:
            role = profile_res.data[0].get("role", "user")
        else:
            print(f"⚠️  Debug - No profile found for user, using default role")
        
        return {
            "user_id": user_res.user.id,
            "email": user_res.user.email,
            "role": role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list):
    """
    Dependency factory to check if user has required role.
    
    Usage:
        @router.get("/admin")
        async def admin_only(user: dict = Depends(require_role([UserRole.ADMIN]))):
            pass
    """
    async def role_checker(user_data: Dict = Depends(get_current_user_with_role)):
        user_role = user_data.get("role")
        
        # Convert allowed_roles to strings for comparison
        allowed_role_values = [role.value if isinstance(role, UserRole) else role for role in allowed_roles]
        
        if user_role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_role_values}"
            )
        return user_data
    
    return role_checker


# Convenience dependencies
async def require_admin(user_data: Dict = Depends(require_role([UserRole.ADMIN]))) -> Dict:
    """Require admin role"""
    return user_data


async def require_user_or_admin(user_data: Dict = Depends(require_role([UserRole.USER, UserRole.ADMIN]))) -> Dict:
    """Require user or admin role"""
    return user_data


async def require_moderator_or_admin(user_data: Dict = Depends(require_role([UserRole.MODERATOR, UserRole.ADMIN]))) -> Dict:
    """Require moderator or admin role"""
    return user_data