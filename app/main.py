from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Imports for our project ---
from app.controllers import file_controller  # Our API routes
from app.config import supabase              # Initializes the Supabase client
# --------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Storage System API",
        description="API for uploading files and retrieving URLs.",
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
    
    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Smart Storage System API!"}

    # Routers
    # This is where we add all our API endpoints
    app.include_router(
        file_controller.router, 
        prefix="/api", 
        tags=["Storage"]
    )

    return app

# This is the main app object uvicorn will use
app = create_app()