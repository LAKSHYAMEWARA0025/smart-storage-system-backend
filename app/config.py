import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Fetch Supabase credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in .env file")

# Initialize the Supabase client
# This one client handles both database and storage
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client initialized successfully.")
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    raise