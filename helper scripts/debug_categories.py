"""
Debug script to check files table and categories
Run this to see what's in your database
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("Checking files table...")
print("=" * 60)

# Get all files
response = supabase.table("files").select("*").execute()

print(f"\nTotal files in database: {len(response.data)}")

if len(response.data) == 0:
    print("\n❌ No files found in database!")
    print("   This is why categories endpoint returns empty.")
else:
    print(f"\n✅ Found {len(response.data)} files")
    
    # Group by user
    users = {}
    for file in response.data:
        user_id = file.get('user_id', 'unknown')
        if user_id not in users:
            users[user_id] = []
        users[user_id].append(file)
    
    print(f"\nFiles by user:")
    for user_id, files in users.items():
        print(f"  User {user_id}: {len(files)} files")
    
    # Group by category
    categories = {}
    for file in response.data:
        category = file.get('category', 'other')
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    print(f"\nFiles by category:")
    for category, count in categories.items():
        print(f"  {category}: {count} files")
    
    # Show sample files
    print(f"\nSample files (first 5):")
    for file in response.data[:5]:
        print(f"  - {file.get('filename')} ({file.get('category')}) - User: {file.get('user_id')}")

print("\n" + "=" * 60)
print("To fix empty categories:")
print("=" * 60)
print("1. Make sure you're logged in as the correct user")
print("2. Check if user_id in files table matches your auth token")
print("3. Clear Redis cache: redis-cli FLUSHALL")
print("4. Upload a new file using /api/media/upload")
print("=" * 60)
