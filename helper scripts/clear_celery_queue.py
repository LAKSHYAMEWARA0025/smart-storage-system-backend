"""
Clear Celery task queue
Use this to remove pending/failed tasks
"""

import redis
from app.config import CELERY_BROKER_URL

print("Clearing Celery task queue...")
print(f"Broker: {CELERY_BROKER_URL}\n")

try:
    # Connect to Redis
    r = redis.from_url(CELERY_BROKER_URL, decode_responses=True)
    
    # Get all Celery keys
    celery_keys = r.keys('celery*')
    
    if not celery_keys:
        print("✅ No Celery tasks in queue")
    else:
        print(f"Found {len(celery_keys)} Celery keys:")
        for key in celery_keys:
            print(f"  - {key}")
        
        # Delete all Celery keys
        deleted = r.delete(*celery_keys)
        print(f"\n✅ Deleted {deleted} keys")
    
    # Also check for any pending tasks
    pending = r.llen('celery')
    if pending:
        print(f"\n⚠️  {pending} tasks still in 'celery' queue")
        r.delete('celery')
        print("✅ Cleared 'celery' queue")
    
    print("\n✅ Celery queue cleared!")
    print("\nYou can now restart your Celery worker:")
    print("  celery -A app.core.celery_app worker --loglevel=info --pool=solo")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nAlternatively, use Celery CLI:")
    print("  celery -A app.core.celery_app purge")
