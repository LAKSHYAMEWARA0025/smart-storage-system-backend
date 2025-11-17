"""
Apply RLS fix directly via Supabase admin client
This script adds the service role policy to the files table
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def apply_rls_fix():
    """Apply the RLS fix by adding service role policy"""
    
    print("=" * 60)
    print("Applying RLS Fix for Files Table")
    print("=" * 60)
    
    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_service_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
        return False
    
    print(f"\n✅ Supabase URL: {supabase_url}")
    print(f"✅ Service key: {supabase_service_key[:20]}...")
    
    # Create admin client
    try:
        supabase = create_client(supabase_url, supabase_service_key)
        print("✅ Admin client created")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return False
    
    # SQL to add service role policy
    sql = """
    CREATE POLICY "Service role bypass RLS" ON files
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
    """
    
    print("\n📝 Applying SQL policy...")
    print(sql)
    
    try:
        # Execute SQL using rpc if available, otherwise use postgrest
        result = supabase.rpc('exec_sql', {'query': sql}).execute()
        print("✅ Policy created successfully!")
        return True
    except Exception as e:
        error_msg = str(e)
        
        if "already exists" in error_msg.lower():
            print("✅ Policy already exists - no action needed!")
            return True
        elif "function exec_sql" in error_msg.lower():
            print("\n⚠️  Cannot execute SQL via API")
            print("\n📋 MANUAL STEPS REQUIRED:")
            print("1. Go to your Supabase Dashboard")
            print("2. Navigate to: SQL Editor")
            print("3. Copy and paste this SQL:")
            print("\n" + "─" * 60)
            print(sql)
            print("─" * 60)
            print("\n4. Click 'Run'")
            print("\n5. Then try uploading a file again")
            return False
        else:
            print(f"❌ Error: {error_msg}")
            return False

def verify_fix():
    """Verify the fix by testing an insert"""
    
    print("\n" + "=" * 60)
    print("Verifying Fix")
    print("=" * 60)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    supabase = create_client(supabase_url, supabase_service_key)
    
    # Test data
    test_data = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "filename": "test_rls_fix.txt",
        "url": "https://test.com/test.txt",
        "file_type": "document",
        "extension": ".txt",
        "file_hash": "test_hash_" + str(hash("test")),
        "file_size": 1024,
        "category": "documents",
        "metadata": {"test": True, "purpose": "RLS verification"}
    }
    
    print("\n🧪 Testing service role INSERT...")
    
    try:
        result = supabase.table("files").insert(test_data).execute()
        
        if result.data:
            print("✅ SUCCESS! Service role can insert into files table")
            print(f"   Inserted test record with ID: {result.data[0].get('id')}")
            
            # Clean up
            record_id = result.data[0].get('id')
            if record_id:
                supabase.table("files").delete().eq("id", record_id).execute()
                print("✅ Test record cleaned up")
            
            print("\n" + "=" * 60)
            print("🎉 FIX VERIFIED - Media uploads should work now!")
            print("=" * 60)
            return True
        else:
            print("⚠️  Insert returned no data")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ FAILED: {error_msg}")
        
        if "row-level security policy" in error_msg.lower():
            print("\n❌ RLS policy still blocking inserts")
            print("\n📋 You need to manually add the policy in Supabase Dashboard:")
            print("\n1. Go to: Supabase Dashboard → SQL Editor")
            print("2. Run this SQL:")
            print("\n" + "─" * 60)
            print("""
CREATE POLICY "Service role bypass RLS" ON files
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
            """)
            print("─" * 60)
        
        return False

if __name__ == "__main__":
    print("\n🚀 Starting RLS Fix Application...\n")
    
    # Try to apply fix
    success = apply_rls_fix()
    
    if not success:
        print("\n⚠️  Automatic fix failed - manual steps required")
        print("See instructions above ☝️")
    
    # Always try to verify
    print("\n" + "─" * 60)
    input("Press Enter to verify the fix (make sure you ran the SQL first)...")
    verify_fix()
