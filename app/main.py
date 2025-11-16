"""
Smart Storage System - Main Application
FastAPI application with graceful startup and shutdown
"""

import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configuration and database initialization
from app.config import init_databases, close_databases, NODE_ENV, ALLOWED_ORIGINS

# Import API router registration
from .api import add_routers

# ============================================================================
# LIFESPAN CONTEXT MANAGER (Startup & Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events
    - Startup: Initialize database connections
    - Shutdown: Close all connections gracefully
    """
    # STARTUP
    print("=" * 60)
    print("🚀 Starting Smart Storage System...")
    print("=" * 60)
    
    try:
        await init_databases()
        print("✅ Application startup complete")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    
    yield
    
    # SHUTDOWN
    print("\n" + "=" * 60)
    print("🛑 Shutting down Smart Storage System...")
    print("=" * 60)
    await close_databases()
    print("✅ Application shutdown complete")
    print("👋 Goodbye!")

# ============================================================================
# CREATE FASTAPI APPLICATION
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title="Smart Storage System API",
        description="Intelligent multi-modal storage system with automatic SQL/NoSQL routing",
        version="1.0.0",
        lifespan=lifespan  # Register lifespan handler
    )

    # CORS Middleware
    origins = ALLOWED_ORIGINS.split(",") if ALLOWED_ORIGINS != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register all routers from api/__init__.py
    add_routers(app)

    return app

# ============================================================================
# SIGNAL HANDLERS FOR GRACEFUL SHUTDOWN
# ============================================================================

def signal_handler(sig, frame):
    """
    Handle shutdown signals (Ctrl+C, SIGTERM)
    """
    print("\n⚠️  Received shutdown signal...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Kill command

# ============================================================================
# CREATE APP INSTANCE
# ============================================================================

# This is the main app object uvicorn will use
app = create_app()

# ============================================================================
# MAIN ENTRY POINT (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting server in {NODE_ENV} mode...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(NODE_ENV == "DEV")
    )