from fastapi import FastAPI

# Routers
from .health import server_health_router

def add_routers(app: FastAPI) -> None:
    app.include_router(server_health_router)