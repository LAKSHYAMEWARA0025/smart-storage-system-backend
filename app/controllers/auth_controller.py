from fastapi import APIRouter, HTTPException, Depends
from app.config import get_supabase
from app.models.auth_model import UserAuth, TokenResponse, UpdateRoleRequest
from app.security import get_current_user_with_role, require_admin
from typing import Dict

router = APIRouter()

@router.post("/signup", response_model=TokenResponse)
async def signup(user_credentials: UserAuth):
    """
    Creates a new user in Supabase Auth and returns access token.
    Auto-logs in the user after successful signup.
    """
    try:
        supabase = get_supabase()
        
        # Sign up the user
        signup_res = supabase.auth.sign_up({
            "email": user_credentials.email,
            "password": user_credentials.password,
        })
        
        if signup_res.user:
            # Auto-login after signup
            login_res = supabase.auth.sign_in_with_password({
                "email": user_credentials.email,
                "password": user_credentials.password
            })
            
            if login_res.session:
                return {
                    "access_token": login_res.session.access_token,
                    "token_type": "bearer",
                    "user_id": signup_res.user.id,
                    "message": "Signup successful"
                }
            else:
                # Fallback if auto-login fails
                return {
                    "access_token": None,
                    "token_type": "bearer",
                    "user_id": signup_res.user.id,
                    "message": "Signup successful. Please login."
                }
        elif signup_res.error:
            raise HTTPException(status_code=400, detail=str(signup_res.error))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserAuth):
    """
    Logs in a user and returns a JWT access token.
    """
    try:
        supabase = get_supabase()
        res = supabase.auth.sign_in_with_password({
            "email": user_credentials.email,
            "password": user_credentials.password
        })
        
        if res.session:
            return {
                "access_token": res.session.access_token,
                "token_type": "bearer"
            }
        elif res.error:
            raise HTTPException(status_code=400, detail=str(res.error))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile")
async def get_profile(user: Dict = Depends(get_current_user_with_role)):
    """
    Get current user profile with role information.
    """
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user["role"]
    }


@router.get("/admin/users")
async def get_all_users(admin: Dict = Depends(require_admin)):
    """
    Admin-only endpoint to get all users with their roles and email addresses.
    """
    try:
        from app.config import get_supabase_admin
        
        supabase_admin = get_supabase_admin()
        
        # Get all user profiles with roles using admin client
        profiles = supabase_admin.table("user_profiles").select("*").order("created_at", desc=True).execute()
        
        # Get user details from auth.users using admin client
        users_data = []
        for profile in profiles.data:
            try:
                # Fetch user from auth.users to get email
                user_response = supabase_admin.auth.admin.get_user_by_id(profile["id"])
                
                if user_response and user_response.user:
                    users_data.append({
                        "user_id": profile["id"],
                        "email": user_response.user.email,
                        "role": profile["role"],
                        "created_at": profile["created_at"],
                        "updated_at": profile["updated_at"]
                    })
                else:
                    # Fallback if user not found in auth
                    users_data.append({
                        "user_id": profile["id"],
                        "email": "unknown",
                        "role": profile["role"],
                        "created_at": profile["created_at"],
                        "updated_at": profile["updated_at"]
                    })
            except Exception as user_error:
                print(f"Error fetching user {profile['id']}: {user_error}")
                users_data.append({
                    "user_id": profile["id"],
                    "email": "error",
                    "role": profile["role"],
                    "created_at": profile["created_at"],
                    "updated_at": profile["updated_at"]
                })
        
        return {
            "total": len(users_data),
            "admin_user": admin["email"],
            "users": users_data
        }
        
    except Exception as e:
        print(f"Error fetching all users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UpdateRoleRequest,
    admin: Dict = Depends(require_admin)
):
    """
    Admin-only endpoint to update user role.
    
    Body: { "new_role": "admin" | "user" | "moderator" }
    """
    new_role = role_data.new_role
    try:
        from app.config import get_supabase_admin
        from datetime import datetime
        
        # Validate role
        valid_roles = ["user", "admin", "moderator"]
        if new_role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Prevent admin from demoting themselves
        if user_id == admin["user_id"] and new_role != "admin":
            raise HTTPException(
                status_code=400,
                detail="You cannot change your own admin role"
            )
        
        supabase_admin = get_supabase_admin()
        
        # Check if user exists
        user_check = supabase_admin.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not user_check.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        old_role = user_check.data[0]["role"]
        
        # Update role in user_profiles using admin client
        result = supabase_admin.table("user_profiles").update({
            "role": new_role,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update role")
        
        # Get user email for response
        try:
            user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
            user_email = user_response.user.email if user_response and user_response.user else "unknown"
        except:
            user_email = "unknown"
        
        return {
            "message": "Role updated successfully",
            "user_id": user_id,
            "user_email": user_email,
            "old_role": old_role,
            "new_role": new_role,
            "updated_by": admin["email"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail=str(e))