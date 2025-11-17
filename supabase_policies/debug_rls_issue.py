"""
Debug script to verify RLS configuration and service role access
Run this to diagnose the RLS issue with file uploads
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def test_rls_configuration():
    """Test RLS configuration and service role access"""
    
    print("=" * 60)
    print("RLS Configuration Debugger")
    print("=" * 60)
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    print("\n1. Checking environment variables...")
    print(f"   SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"   SUPABASE_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")
    print(f"   SUPABASE_SERVICE_KEY: {'✅ Set' if supabase_service_key else '❌ Missing'}")
    
    if not all([supabase_url, supabase_key, supabase_service_key]):
        print("\n❌ Missing required environment variables!")
        return
    
    # Create clients
    print("\n2. Creating Supabase clients...")
    try:
        supabase_user = create_client(supabase_url, supabase_key)
        supabase_admin = create_client(supabase_url, supabase_service_key)
        print("   ✅ Clients created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create clients: {e}")
        return
    
    # Test service role access
    print("\n3. Testing service role access to files table...")
    try:
        # Try to select from files table with service role
        result = supabase_admin.table("files").select("id").limit(1).execute()
        print(f"   ✅ Service role can SELECT from files table")
        print(f"   Found {len(result.data)} records")
    except Exception as e:
        print(f"   ❌ Service role SELECT failed: {e}")
    
    # Test insert with service role
    print("\n4. Testing service role INSERT capability...")
    test_data = {
        "user_id": "00000000-0000-0000-0000-000000000000",  # Test UUID
        "filename": "test_rls_debug.txt",
        "url": "https://test.com/test.txt",
        "file_type": "document",
        "extension": ".txt",
        "file_hash": "test_hash_12345",
        "file_size": 1024,
        "category": "documents",
        "metadata": {"test": True}
    }
    
    try:
        result = supabase_admin.table("files").insert(test_data).execute()
        print(f"   ✅ Service role can INSERT into files table")
        print(f"   Inserted record ID: {result.data[0].get('id') if result.data else 'N/A'}")
        
        # Clean up test record
        if result.data and result.data[0].get('id'):
            supabase_admin.table("files").delete().eq("id", result.data[0]['id']).execute()
            print(f"   ✅ Test record cleaned up")
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Service role INSERT failed: {error_msg}")
        
        if "row-level security policy" in error_msg.lower():
            print("\n" + "=" * 60)
            print("🔍 DIAGNOSIS: RLS Policy Violation Detected!")
            print("=" * 60)
            print("\nThe service role is being blocked by RLS policies.")
            print("\nSOLUTION:")
            print("1. Go to your Supabase SQL Editor")
            print("2. Run the SQL script in 'fix_rls_policy.sql'")
            print("3. This will add proper RLS policies that allow service role access")
            print("\nAlternatively, you can disable RLS on the files table:")
            print("   ALTER TABLE files DISABLE ROW LEVEL SECURITY;")
            print("\n(Note: Disabling RLS is less secure but simpler)")
    
    # Check RLS status
    print("\n5. Checking RLS status on files table...")
    try:
        query = """
        SELECT 
            schemaname,
            tablename,
            rowsecurity as rls_enabled
        FROM pg_tables
        WHERE tablename = 'files';
        """
        result = supabase_admin.rpc('exec_sql', {'query': query}).execute()
        print(f"   Result: {result.data}")
    except Exception as e:
        print(f"   ⚠️  Could not check RLS status: {e}")
        print("   You can check manually in Supabase Dashboard > Table Editor > files > Settings")
    
    print("\n" + "=" * 60)
    print("Debug complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_rls_configuration()
