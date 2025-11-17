"""
Test the exact query that the endpoint uses
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

user_id = "955a1bcb-fff7-4ead-9d1c-d2f038b41bb0"

print("=" * 60)
print("Testing categories query")
print("=" * 60)

# Test 1: Get all files for user
print(f"\nTest 1: Get all files for user {user_id}")
res1 = supabase.table("files").select("*").eq("user_id", user_id).execute()
print(f"Result: {len(res1.data)} files")
if res1.data:
    print("Sample file:")
    print(res1.data[0])

# Test 2: Get just extension and category (what the endpoint does)
print(f"\nTest 2: Get extension and category only")
res2 = supabase.table("files").select("extension, category").eq("user_id", user_id).execute()
print(f"Result: {len(res2.data)} records")
print(f"Data: {res2.data}")

# Test 3: Check user_id type
print(f"\nTest 3: Check user_id type in database")
res3 = supabase.table("files").select("user_id").limit(5).execute()
print("Sample user_ids from database:")
for file in res3.data:
    print(f"  - {file['user_id']} (type: {type(file['user_id'])})")

# Test 4: Try with string conversion
print(f"\nTest 4: Try with str() conversion")
res4 = supabase.table("files").select("extension, category").eq("user_id", str(user_id)).execute()
print(f"Result: {len(res4.data)} records")

print("\n" + "=" * 60)
