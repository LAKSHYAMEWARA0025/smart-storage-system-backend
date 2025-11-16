"""
Celery Monitoring Script
Monitor Celery workers and tasks
"""

from app.workers import celery_app
from celery import Celery

def check_worker_status():
    """Check if workers are running"""
    inspect = celery_app.control.inspect()
    
    print("=" * 60)
    print("CELERY WORKER STATUS")
    print("=" * 60)
    
    # Check active workers
    active = inspect.active()
    if active:
        print(f"\n✅ Active Workers: {len(active)}")
        for worker, tasks in active.items():
            print(f"   {worker}: {len(tasks)} active tasks")
    else:
        print("\n❌ No active workers found")
    
    # Check registered tasks
    registered = inspect.registered()
    if registered:
        print(f"\n📋 Registered Tasks:")
        for worker, tasks in registered.items():
            print(f"   {worker}:")
            for task in tasks:
                print(f"      - {task}")
    
    # Check stats
    stats = inspect.stats()
    if stats:
        print(f"\n📊 Worker Stats:")
        for worker, stat in stats.items():
            print(f"   {worker}:")
            print(f"      Pool: {stat.get('pool', {}).get('implementation', 'N/A')}")
            print(f"      Max concurrency: {stat.get('pool', {}).get('max-concurrency', 'N/A')}")
    
    print("\n" + "=" * 60)


def check_queue_status():
    """Check queue status"""
    inspect = celery_app.control.inspect()
    
    print("\n" + "=" * 60)
    print("QUEUE STATUS")
    print("=" * 60)
    
    # Check reserved tasks
    reserved = inspect.reserved()
    if reserved:
        print(f"\n📦 Reserved Tasks:")
        for worker, tasks in reserved.items():
            print(f"   {worker}: {len(tasks)} tasks")
    else:
        print("\n✅ No reserved tasks")
    
    # Check scheduled tasks
    scheduled = inspect.scheduled()
    if scheduled:
        print(f"\n⏰ Scheduled Tasks:")
        for worker, tasks in scheduled.items():
            print(f"   {worker}: {len(tasks)} tasks")
    else:
        print("\n✅ No scheduled tasks")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'workers':
            check_worker_status()
        elif command == 'queues':
            check_queue_status()
        elif command == 'all':
            check_worker_status()
            check_queue_status()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python celery_monitor.py [workers|queues|all]")
    else:
        # Default: show all
        check_worker_status()
        check_queue_status()
