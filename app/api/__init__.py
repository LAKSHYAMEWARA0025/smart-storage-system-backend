from fastapi import FastAPI

# Import routers
from .health import server_health_router
from .upload import router as upload_router
from .query import router as query_router
from .entities import router as entities_router
from .media import router as media_router
from app.controllers import auth_controller
from app.controllers import file_controller

def add_routers(app: FastAPI) -> None:
    """
    Register all API routers
    This is the centralized place for all route registration
    """
    # Health check
    app.include_router(server_health_router)
    
    # Authentication
    app.include_router(
        auth_controller.router,
        prefix="/auth",
        tags=["Authentication"]
    )
    
    # File Storage (Media) - Legacy
    app.include_router(
        file_controller.router,
        prefix="/api",
        tags=["File Storage (Legacy)"]
    )
    
    # Media Upload (Background Processing)
    app.include_router(
        media_router,
        prefix="/api",
        tags=["Media Upload"]
    )
    
    # Structured Data Upload
    app.include_router(
        upload_router,
        prefix="/api",
        tags=["Data Upload"]
    )
    
    # Query Interface
    app.include_router(
        query_router,
        prefix="/api",
        tags=["Query"]
    )
    
    # Entity Management
    app.include_router(
        entities_router,
        prefix="/api",
        tags=["Entities"]
    )