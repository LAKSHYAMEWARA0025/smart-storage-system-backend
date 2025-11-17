# Celery Auto-Retry Explained

## What Happened

When you started the Celery worker, it automatically picked up and retried a previously failed job:

```
Task app.workers.upload_worker.process_upload_task[c552d122-1edf-444f-9569-03f9f285ebb7] received
```

## Why This Happens

1. **Previous Job Failed** - Your upload job failed with the duplicate key error
2. **Retry Configuration** - The worker is configured with `max_retries=3`
3. **Persistent Queue** - Failed tasks are stored in Redis
4. **Worker Restart** - When you restart the worker, it picks up pending retries

## The Configuration

In `app/workers/upload_worker.py`:

```python
@celery_app.task(
    bind=True,
    base=UploadTask,
    name='app.workers.upload_worker.process_upload_task',
    max_retries=3,           # ← Will retry up to 3 times
    default_retry_delay=60   # ← Wait 60 seconds between retries
)
```

## The New Error

```
'str' object has no attribute 'get'
```

This was a bug I introduced when trying to access the conflict data. **This has been fixed.**

## How to Handle This

### Option 1: Clear the Queue (Recommended)

Stop the worker and clear all pending tasks:

```bash
# Stop worker (Ctrl+C)

# Clear queue
python clear_celery_queue.py

# Or use Celery CLI
celery -A app.core.celery_app purge

# Restart worker
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

### Option 2: Let It Retry (Should Work Now)

The bug is fixed, so the next retry should succeed. Just wait for it to retry (60 seconds).

### Option 3: Wait for Max Retries

After 3 failed attempts, Celery will give up and mark the task as permanently failed.

## Preventing Auto-Retry

If you don't want automatic retries, modify the task configuration:

```python
@celery_app.task(
    bind=True,
    base=UploadTask,
    name='app.workers.upload_worker.process_upload_task',
    max_retries=0,           # ← No retries
    default_retry_delay=60
)
```

## Monitoring Tasks

### Check Redis Queue

```bash
redis-cli
> LLEN celery
> KEYS celery*
```

### Check Task Status

```python
from app.models.mongo_models import UploadJobModel

# Get job status
job = UploadJobModel.objects(job_id="c4354095-a53d-4292-b73a-f85b3ae5e668").first()
print(f"Status: {job.status}")
print(f"Error: {job.error_message}")
```

## Best Practices

1. **Clear queue after fixing bugs** - Prevents old failed tasks from retrying
2. **Monitor retry counts** - Set appropriate `max_retries` for your use case
3. **Use exponential backoff** - For transient errors (network, DB connection)
4. **Log retry attempts** - Track why tasks are failing

## Related Files

- `app/workers/upload_worker.py` - Task configuration and retry logic
- `app/core/celery_app.py` - Celery app configuration
- `clear_celery_queue.py` - Helper script to clear queue
