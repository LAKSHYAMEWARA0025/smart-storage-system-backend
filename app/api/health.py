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


@server_health_router.get("/apis",
    summary="List All Available APIs",
    description="Returns comprehensive documentation of all available API endpoints with descriptions, parameters, and examples",
    response_description="Complete API documentation"
)
async def list_apis():
    """
    Get a complete list of all available API endpoints with detailed information
    """
    return {
        "version": "1.0.0",
        "base_url": "/api",
        "authentication": {
            "type": "Bearer Token",
            "header": "Authorization: Bearer {token}",
            "note": "Required for all endpoints except /health, /auth/register, and /auth/login"
        },
        "endpoints": {
            "authentication": [
                {
                    "method": "POST",
                    "path": "/auth/register",
                    "description": "Register a new user account",
                    "auth_required": False,
                    "body": {
                        "email": "user@example.com",
                        "password": "securepassword",
                        "full_name": "John Doe"
                    },
                    "response": {
                        "user_id": "uuid",
                        "email": "user@example.com",
                        "token": "jwt_token"
                    }
                },
                {
                    "method": "POST",
                    "path": "/auth/login",
                    "description": "Login with email and password",
                    "auth_required": False,
                    "body": {
                        "email": "user@example.com",
                        "password": "securepassword"
                    },
                    "response": {
                        "access_token": "jwt_token",
                        "token_type": "bearer",
                        "user": {"id": "uuid", "email": "user@example.com"}
                    }
                },
                {
                    "method": "GET",
                    "path": "/auth/me",
                    "description": "Get current authenticated user information",
                    "auth_required": True,
                    "response": {
                        "id": "uuid",
                        "email": "user@example.com",
                        "full_name": "John Doe"
                    }
                }
            ],
            "media_upload": [
                {
                    "method": "POST",
                    "path": "/api/media/upload",
                    "description": "Upload media files (images/videos) with background processing",
                    "auth_required": True,
                    "content_type": "multipart/form-data",
                    "body": {
                        "files": ["file1.jpg", "file2.mp4"]
                    },
                    "limits": {
                        "max_files": 10,
                        "max_file_size": "50MB",
                        "allowed_types": ["image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/quicktime", "video/webm"]
                    },
                    "response": {
                        "job_id": "uuid",
                        "status": "queued",
                        "total_files": 2,
                        "message": "Upload queued for processing",
                        "status_url": "/api/media/upload/status/{job_id}"
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/media/upload/status/{job_id}",
                    "description": "Check media upload job status and progress",
                    "auth_required": True,
                    "params": {
                        "job_id": "Job ID returned from upload endpoint"
                    },
                    "response": {
                        "job_id": "uuid",
                        "status": "processing|completed|failed",
                        "progress": {
                            "current": 1,
                            "total": 2,
                            "percentage": 50.0,
                            "stage": "uploading"
                        },
                        "uploaded_files": [
                            {
                                "filename": "file1.jpg",
                                "url": "storage_url",
                                "public_url": "https://...",
                                "size_bytes": 123456,
                                "metadata": {}
                            }
                        ],
                        "failed_files": []
                    }
                }
            ],
            "file_management": [
                {
                    "method": "GET",
                    "path": "/api/files/categories",
                    "description": "Get all file categories with counts and file extensions",
                    "auth_required": True,
                    "query_params": {
                        "refresh": "boolean (optional) - Bypass cache and get fresh data"
                    },
                    "response": {
                        "categories": [
                            {
                                "name": "images",
                                "count": 10,
                                "extensions": [".jpg", ".png"]
                            },
                            {
                                "name": "videos",
                                "count": 5,
                                "extensions": [".mp4"]
                            }
                        ]
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/files/by-category",
                    "description": "Get files filtered by one or more categories",
                    "auth_required": True,
                    "query_params": {
                        "categories": "string (required) - Comma-separated category names (e.g., 'images,videos')",
                        "refresh": "boolean (optional) - Bypass cache and get fresh data"
                    },
                    "example": "/api/files/by-category?categories=images,videos&refresh=true",
                    "response": {
                        "total": 15,
                        "categories": ["images", "videos"],
                        "files": [
                            {
                                "id": "uuid",
                                "filename": "photo.jpg",
                                "url": "https://...",
                                "category": "images",
                                "file_size": 123456,
                                "created_at": "2024-03-15T10:00:00Z"
                            }
                        ]
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/files",
                    "description": "List all files for the authenticated user",
                    "auth_required": True,
                    "response": {
                        "files": [
                            {
                                "id": "uuid",
                                "filename": "document.pdf",
                                "url": "https://...",
                                "category": "documents",
                                "file_size": 234567
                            }
                        ]
                    }
                },
                {
                    "method": "DELETE",
                    "path": "/api/files/{file_id}",
                    "description": "Delete a specific file",
                    "auth_required": True,
                    "params": {
                        "file_id": "UUID of the file to delete"
                    },
                    "response": {
                        "message": "File deleted successfully"
                    }
                }
            ],
            "data_upload": [
                {
                    "method": "POST",
                    "path": "/api/data/upload/analyze",
                    "description": "Analyze JSON/CSV files and detect schemas",
                    "auth_required": True,
                    "content_type": "multipart/form-data",
                    "body": {
                        "files": ["data.json", "data.csv"]
                    },
                    "response": {
                        "analysis_id": "uuid",
                        "schemas_detected": [
                            {
                                "schema_id": "uuid",
                                "fields": {"name": "string", "age": "integer"},
                                "record_count": 100,
                                "storage_recommendation": "sql|nosql",
                                "null_density": 5.2
                            }
                        ],
                        "variance_level": "low|normal|high|extreme",
                        "recommendation": {},
                        "requires_decision": True
                    }
                },
                {
                    "method": "POST",
                    "path": "/api/data/upload/execute",
                    "description": "Execute data upload after analysis",
                    "auth_required": True,
                    "body": {
                        "analysis_id": "uuid",
                        "decisions": {
                            "schema_id": {
                                "action": "create|evolve|new_table",
                                "custom_name": "table_name"
                            }
                        },
                        "user_override": False,
                        "acknowledge_risks": False
                    },
                    "response": {
                        "job_id": "uuid",
                        "status": "queued",
                        "message": "Upload job created"
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/data/upload/status/{job_id}",
                    "description": "Check data upload job status",
                    "auth_required": True,
                    "params": {
                        "job_id": "Job ID from execute endpoint"
                    },
                    "response": {
                        "job_id": "uuid",
                        "status": "queued|processing|completed|failed",
                        "progress": {
                            "current": 50,
                            "total": 100,
                            "percentage": 50.0
                        }
                    }
                }
            ],
            "query": [
                {
                    "method": "POST",
                    "path": "/api/query/execute",
                    "description": "Execute SQL or NoSQL queries",
                    "auth_required": True,
                    "body": {
                        "query": "SELECT * FROM users WHERE age > 25",
                        "entity_name": "users",
                        "storage_type": "sql|nosql"
                    },
                    "response": {
                        "results": [],
                        "row_count": 10,
                        "execution_time_ms": 45
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/query/history",
                    "description": "Get query execution history",
                    "auth_required": True,
                    "response": {
                        "queries": [
                            {
                                "query": "SELECT * FROM users",
                                "executed_at": "2024-03-15T10:00:00Z",
                                "execution_time_ms": 45,
                                "row_count": 100
                            }
                        ]
                    }
                }
            ],
            "entities": [
                {
                    "method": "GET",
                    "path": "/api/entities",
                    "description": "List all entities (tables/collections) for the user",
                    "auth_required": True,
                    "response": {
                        "entities": [
                            {
                                "name": "users",
                                "storage_type": "sql",
                                "record_count": 1000,
                                "created_at": "2024-03-15T10:00:00Z"
                            }
                        ]
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/entities/{entity_name}",
                    "description": "Get detailed information about a specific entity",
                    "auth_required": True,
                    "params": {
                        "entity_name": "Name of the entity"
                    },
                    "response": {
                        "name": "users",
                        "storage_type": "sql",
                        "fields": [
                            {"name": "id", "type": "integer"},
                            {"name": "name", "type": "string"}
                        ],
                        "record_count": 1000
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/entities/{entity_name}/data",
                    "description": "Get paginated data from an entity",
                    "auth_required": True,
                    "params": {
                        "entity_name": "Name of the entity"
                    },
                    "query_params": {
                        "page": "integer (default: 1)",
                        "limit": "integer (default: 50, max: 1000)"
                    },
                    "example": "/api/entities/users/data?page=1&limit=50",
                    "response": {
                        "data": [],
                        "total": 1000,
                        "page": 1,
                        "limit": 50,
                        "pages": 20
                    }
                }
            ],
            "health": [
                {
                    "method": "GET",
                    "path": "/health",
                    "description": "Server health check with system metrics",
                    "auth_required": False,
                    "response": {
                        "status": "Running",
                        "timestamp": "2024-03-15T10:00:00Z",
                        "server": {
                            "os": "Linux",
                            "memory": {},
                            "cpu": {}
                        }
                    }
                },
                {
                    "method": "GET",
                    "path": "/apis",
                    "description": "This endpoint - List all available APIs",
                    "auth_required": False,
                    "response": "Complete API documentation"
                }
            ]
        },
        "notes": {
            "rate_limiting": "Not implemented yet",
            "pagination": "Most list endpoints support page and limit query parameters",
            "caching": "File and query endpoints use Redis caching with 1-hour TTL",
            "background_jobs": "Media and data uploads are processed asynchronously via Celery"
        }
    }