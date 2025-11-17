"""
Check the schema of the files table
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("Checking files table schema")
print("=" * 60)

# Get a sample record to see all columns
res = supabase.table("files").select("*").limit(1).execute()

if res.data:
    print("\nColumns in files table:")
    for key in res.data[0].keys():
        print(f"  - {key}")
    
    print("\nSample record:")
    for key, value in res.data[0].items():
        print(f"  {key}: {value}")
else:
    print("\nNo records found in files table")

print("\n" + "=" * 60)
