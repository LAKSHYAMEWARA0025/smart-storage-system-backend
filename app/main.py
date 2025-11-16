from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Imports for our project ---
from app.controllers import file_controller  # Our storage routes
from app.controllers import auth_controller  # Our new auth routes
from app.config import supabase              # Initializes the Supabase client

from .api import add_routers
# --------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Storage System API",
        description="API for uploading files, retrieving URLs, and authentication.",
        version="1.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routers
    add_routers(app)

    # Routers
    app.include_router(
        auth_controller.router, 
        prefix="/auth", 
        tags=["Auth"]
    )
    app.include_router(
        file_controller.router, 
        prefix="/api", 
        tags=["Storage"]
    )

    return app

# This is the main app object uvicorn will use
app = create_app()