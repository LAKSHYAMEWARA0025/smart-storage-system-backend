"""
Celery Worker Startup Script
Run this to start the Celery worker for background task processing
"""

import sys
from app.workers import celery_app

if __name__ == '__main__':
    # Start Celery worker
    argv = [
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Number of worker processes
        '--queues=upload_queue',  # Queue to consume from
        '--hostname=worker@%h',
    ]
    
    celery_app.worker_main(argv)
