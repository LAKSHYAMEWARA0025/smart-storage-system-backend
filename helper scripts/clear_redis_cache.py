"""
Clear Redis Cache Script
Clears specific cache keys or all cache
"""

import asyncio
import os
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")


async def clear_cache(pattern=None):
    """
    Clear Redis cache
    
    Args:
        pattern: Optional pattern to match keys (e.g., "file_categories:*")
                 If None, clears ALL cache
    """
    print("=" * 60)
    print("Redis Cache Cleaner")
    print("=" * 60)
    
    try:
        # Connect to Redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Test connection
        await redis_client.ping()
        print("✅ Connected to Redis")
        
        if pattern:
            # Clear specific pattern
            print(f"\n🔍 Searching for keys matching: {pattern}")
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                print(f"Found {len(keys)} keys:")
                for key in keys:
                    print(f"  - {key}")
                
                # Delete keys
                deleted = await redis_client.delete(*keys)
                print(f"\n🗑️  Deleted {deleted} keys")
            else:
                print("No keys found matching pattern")
        else:
            # Clear all cache
            print("\n⚠️  Clearing ALL cache...")
            await redis_client.flushall()
            print("🗑️  All cache cleared!")
        
        await redis_client.close()
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function with menu"""
    print("\nWhat would you like to clear?")
    print("1. File categories cache only")
    print("2. All file-related cache")
    print("3. Everything (FLUSHALL)")
    print("4. Custom pattern")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        # Clear file categories for all users
        await clear_cache("file_categories:*")
    elif choice == "2":
        # Clear all file-related cache
        patterns = ["file_categories:*", "files:*", "files_by_category:*"]
        for pattern in patterns:
            await clear_cache(pattern)
    elif choice == "3":
        # Clear everything
        confirm = input("⚠️  This will clear ALL cache. Are you sure? (yes/no): ").strip().lower()
        if confirm == "yes":
            await clear_cache(None)
        else:
            print("Cancelled")
    elif choice == "4":
        # Custom pattern
        pattern = input("Enter pattern (e.g., 'file_categories:*'): ").strip()
        await clear_cache(pattern)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
