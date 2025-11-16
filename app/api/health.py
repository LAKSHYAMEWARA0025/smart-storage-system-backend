from fastapi import APIRouter, status
from datetime import datetime
import platform
import psutil

server_health_router = APIRouter(
    prefix="",
    tags=["Health"],
    responses={
        200: {"description": "Server is Up and Running"},
        503: {"description": "Server is Down"},
    },
)

@server_health_router.get("/",
    summary="Server Health Check",
    description="Returns detailed server health information including memory usage, CPU load, and uptime",
    response_description="Server health metrics"
)
async def health_check():
    try:
        health_info = {
            "status": "Running",
            "timestamp": datetime.now().isoformat(),
            "server": {
                "os": platform.system(),
                "python_version": platform.python_version(),
                "memory": {
                    "total": f"{psutil.virtual_memory().total / (1024 * 1024 * 1024):.2f}GB",
                    "available": f"{psutil.virtual_memory().available / (1024 * 1024 * 1024):.2f}GB",
                    "percent_used": f"{psutil.virtual_memory().percent}%"
                },
                "cpu": {
                    "usage_percent": f"{psutil.cpu_percent()}%",
                    "cores": psutil.cpu_count()
                }
            }
        }
        return health_info
    except Exception as e:
        return {
            "status": "Down",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status.HTTP_503_SERVICE_UNAVAILABLE