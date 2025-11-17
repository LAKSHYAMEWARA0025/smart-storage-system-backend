"""
Celery Application Configuration
Configures Celery for background task processing
"""

import ssl
from celery import Celery
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Create Celery app
celery_app = Celery(
    "smart_storage",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        'app.workers.upload_worker',
        'app.workers.media_worker'
    ]  # Import worker modules
)

# SSL configuration for rediss:// URLs
broker_use_ssl = None
redis_backend_use_ssl = None

if CELERY_BROKER_URL.startswith('rediss://'):
    broker_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_check_hostname': False
    }

if CELERY_RESULT_BACKEND.startswith('rediss://'):
    redis_backend_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_check_hostname': False
    }

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    result_backend_transport_options={'global_keyprefix': 'celery_result_'},
    broker_transport_options={'global_keyprefix': 'celery_broker_'},
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    
    # Retry settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # Ensure async execution (never run tasks synchronously)
    task_always_eager=False,
    task_eager_propagates=False,
    
    # SSL settings
    broker_use_ssl=broker_use_ssl,
    redis_backend_use_ssl=redis_backend_use_ssl,
)

print("✅ Celery app configured")
