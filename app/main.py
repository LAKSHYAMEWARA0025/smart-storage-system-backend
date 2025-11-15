from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
def create_app() -> FastAPI:
    app = FastAPI(
        title="My API",
        description="Production-ready FastAPI backend",
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
        return {"message": "Hello, FastAPI!"}

    # Routers
    # app.include_router(api_router, prefix="/api/v1")

    return app

app = create_app()