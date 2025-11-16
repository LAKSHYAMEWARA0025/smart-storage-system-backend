"""
Development Runner
Starts both FastAPI and Celery worker in parallel
"""

import subprocess
import sys
import os
from multiprocessing import Process

def run_fastapi():
    """Run FastAPI with hot reload"""
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])

def run_celery():
    """Run Celery worker"""
    subprocess.run([
        sys.executable, "-m", "celery",
        "-A", "app.core.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo"
    ])

if __name__ == "__main__":
    print("🚀 Starting development environment...")
    print("📡 FastAPI: http://localhost:8000")
    print("⚙️  Celery Worker: Starting...")
    print("\nPress Ctrl+C to stop all services\n")
    
    # Start both processes
    fastapi_process = Process(target=run_fastapi)
    celery_process = Process(target=run_celery)
    
    try:
        fastapi_process.start()
        celery_process.start()
        
        fastapi_process.join()
        celery_process.join()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        fastapi_process.terminate()
        celery_process.terminate()
        fastapi_process.join()
        celery_process.join()
        print("✅ All services stopped")
