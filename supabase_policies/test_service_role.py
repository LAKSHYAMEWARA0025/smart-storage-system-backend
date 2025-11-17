"""
Quick test to verify service role can insert into files table
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

print("Testing service role access to files table...")
print(f"URL: {supabase_url}")
print(f"Key: {supabase_service_key[:20]}...\n")

supabase = create_client(supabase_url, supabase_service_key)

# Test data
test_data = {
    "user_id": "955a1bcb-fff7-4ead-9d1c-d2f038b41bb0",  # Your actual user ID from the error
    "filename": "test_rls.txt",
    "url": "https://test.com/test.txt",
    "file_type": "document",
    "extension": ".txt",
    "file_hash": "test_hash_12345",
    "file_size": 1024,
    "category": "documents",
    "metadata": {"test": True}
}

try:
    print("Attempting INSERT with service role...")
    result = supabase.table("files").insert(test_data).execute()
    print("✅ SUCCESS! Service role can insert")
    print(f"Result: {result.data}")
    
    # Clean up
    if result.data and result.data[0].get('id'):
        supabase.table("files").delete().eq("id", result.data[0]['id']).execute()
        print("✅ Test record cleaned up")
        
except Exception as e:
    print(f"❌ FAILED: {e}")
    print("\n🔧 FIX REQUIRED:")
    print("Run this SQL in Supabase Dashboard → SQL Editor:\n")
    print("CREATE POLICY \"Service role bypass RLS\" ON files")
    print("FOR ALL TO service_role USING (true) WITH CHECK (true);")
