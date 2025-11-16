import os
from supabase import create_client, Client
from dotenv import load_dotenv
import redis.asyncio as redis  # <-- Import async Redis

# Load .env
load_dotenv()

# --- Supabase Setup ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# ... (supabase client init) ...
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client initialized successfully.")
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    raise

# --- Redis Setup ---
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is not set!")

try:
    # Create the async Redis client
    redis_client = redis.from_url(
        REDIS_URL, 
        decode_responses=True # <-- So we get strings, not bytes
    )
    print("Redis client initialized successfully.")
except Exception as e:
    print(f"Error initializing Redis client: {e}")
    raise