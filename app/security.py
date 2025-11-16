from fastapi import Depends, HTTPException, status
# 1. Import HTTPBearer instead
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import supabase

# 2. Use HTTPBearer() - it's simpler
oauth2_scheme = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """
    Dependency that verifies the JWT and returns the user's ID.
    This will be run on every protected endpoint.
    """
    
    # 3. Get the token from the 'auth' object
    token = auth.credentials 
    
    try:
        # supabase.auth.get_user() validates the token and returns the user
        res = supabase.auth.get_user(token)
        
        if not res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Return the user's ID (which is a UUID)
        return res.user.id
        
    except Exception as e:
        # This handles errors if the token is malformed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )