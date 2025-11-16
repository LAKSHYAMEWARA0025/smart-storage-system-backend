from fastapi import APIRouter, HTTPException
from app.config import supabase
from app.models.auth_model import UserAuth, TokenResponse

router = APIRouter()

@router.post("/signup")
async def signup(user_credentials: UserAuth):
    """
    Creates a new user in Supabase Auth.
    """
    try:
        res = supabase.auth.sign_up({
            "email": user_credentials.email,
            "password": user_credentials.password,
        })
        
        if res.user:
            return {"message": "Signup successful. Please check your email to verify.", "user_id": res.user.id}
        elif res.error:
            raise HTTPException(status_code=400, detail=str(res.error))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserAuth):
    """
    Logs in a user and returns a JWT access token.
    """
    try:
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