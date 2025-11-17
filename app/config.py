"""
Configuration module for Smart Storage System
Handles all external service connections and environment variables
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mongoengine import connect, disconnect
from urllib.parse import quote_plus, urlparse, urlunparse
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# ============================================================================
# ENVIRONMENT VARIABLE VALIDATION
# ============================================================================

class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass

def get_env(key: str, required: bool = True, default: Optional[str] = None) -> str:
    """
    Get environment variable with validation
    
    Args:
        key: Environment variable name
        required: Whether the variable is required
        default: Default value if not required
        
    Returns:
        Environment variable value
        
    Raises:
        ConfigurationError: If required variable is missing
    """
    value = os.getenv(key, default)
    if required and value is None:
        raise ConfigurationError(f"Required environment variable '{key}' is not set")
    return value

# ============================================================================
# LOAD AND VALIDATE ENVIRONMENT VARIABLES
# ============================================================================

try:
    print("🔧 Loading configuration...")
    
    # App Configuration
    NODE_ENV = get_env("NODE_ENV", required=False, default="DEV")
    ALLOWED_ORIGINS = get_env("ALLOWED_ORIGINS", required=False, default="*")
    
    # Supabase
    SUPABASE_URL = get_env("SUPABASE_URL", required=True)
    SUPABASE_KEY = get_env("SUPABASE_KEY", required=True)
    SUPABASE_SERVICE_KEY = get_env("SUPABASE_SERVICE_KEY", required=True)
    SUPABASE_DB_URL = get_env("SUPABASE_DB_URL", required=True)
    SUPABASE_BUCKET_NAME = get_env("SUPABASE_BUCKET_NAME", required=False, default="media")
    
    # MongoDB
    MONGO_URI = get_env("MONGO_URI", required=True)
    MONGO_DB_NAME = get_env("MONGO_DB_NAME", required=False, default="smart_storage")
    
    # Redis
    REDIS_URL = get_env("REDIS_URL", required=True)
    REDIS_UPLOAD_DATA_TTL = int(get_env("REDIS_UPLOAD_DATA_TTL", required=False, default="1800"))  # 30 minutes
    
    # Celery
    CELERY_BROKER_URL = get_env("CELERY_BROKER_URL", required=False, default=REDIS_URL)
    CELERY_RESULT_BACKEND = get_env("CELERY_RESULT_BACKEND", required=False, default=REDIS_URL)
    
    print(f"📊 Celery broker: {CELERY_BROKER_URL}")
    print(f"📊 Celery backend: {CELERY_RESULT_BACKEND}")
    
    # File Upload Limits
    MAX_MEDIA_FILE_SIZE_MB = int(get_env("MAX_MEDIA_FILE_SIZE_MB", required=False, default="50"))
    MAX_DATA_FILE_SIZE_MB = int(get_env("MAX_DATA_FILE_SIZE_MB", required=False, default="50"))
    MAX_FILES_PER_UPLOAD = int(get_env("MAX_FILES_PER_UPLOAD", required=False, default="10"))
    
    # Convert to bytes
    MAX_MEDIA_FILE_SIZE = MAX_MEDIA_FILE_SIZE_MB * 1024 * 1024
    MAX_DATA_FILE_SIZE = MAX_DATA_FILE_SIZE_MB * 1024 * 1024
    
    # Storage Decision Thresholds
    NULL_DENSITY_THRESHOLD = float(get_env("NULL_DENSITY_THRESHOLD", required=False, default="0.20"))
    FIELD_OVERLAP_THRESHOLD = float(get_env("FIELD_OVERLAP_THRESHOLD", required=False, default="0.70"))
    TYPE_CONSISTENCY_THRESHOLD = float(get_env("TYPE_CONSISTENCY_THRESHOLD", required=False, default="0.90"))
    
    # System Limits
    MAX_INDEXES_PER_ENTITY = int(get_env("MAX_INDEXES_PER_ENTITY", required=False, default="5"))
    FAILED_RECORDS_TTL_DAYS = int(get_env("FAILED_RECORDS_TTL_DAYS", required=False, default="7"))
    MAX_COLLECTIONS_PER_UPLOAD = int(get_env("MAX_COLLECTIONS_PER_UPLOAD", required=False, default="20"))
    VARIANCE_THRESHOLD_MULTIPLIER = float(get_env("VARIANCE_THRESHOLD_MULTIPLIER", required=False, default="1.0"))
    
    print("✅ Configuration loaded successfully")
    print(f"📊 Environment: {NODE_ENV}")
    print(f"📊 Max media file size: {MAX_MEDIA_FILE_SIZE_MB}MB")
    print(f"📊 Max data file size: {MAX_DATA_FILE_SIZE_MB}MB")
    
except ConfigurationError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file and ensure all required variables are set")
    sys.exit(1)
except ValueError as e:
    print(f"❌ Configuration Value Error: {e}")
    print("Please check that numeric environment variables have valid values")
    sys.exit(1)

# ============================================================================
# DATABASE CONNECTIONS (Global instances)
# ============================================================================

# Supabase Client
supabase: Client = None
supabase_admin: Client = None  # Service role client for admin operations

# Redis Client
redis_client = None

# SQLAlchemy Engine (for Supabase PostgreSQL)
sql_engine = None
SessionLocal = None

# MongoDB Clients
mongo_client = None  # Motor client for async operations
mongodb = None       # Motor database instance

# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

async def init_databases():
    """
    Initialize all database connections
    Called on application startup
    """
    global supabase, supabase_admin, redis_client, sql_engine, SessionLocal, mongo_client, mongodb
    
    print("🚀 Initializing database connections...")
    
    try:
        # 1. Supabase Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase client initialized")
        
        # 2. SQLAlchemy Engine (for Supabase PostgreSQL)
        sql_engine = create_engine(
            SUPABASE_DB_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sql_engine)
        print("✅ PostgreSQL connection established")
        
        # 3. MongoDB - MongoEngine (for schema registry)
        # Handle MongoDB URI - if it contains username/password, they should be URL encoded
        try:
            connect(
                db=MONGO_DB_NAME,
                host=MONGO_URI,
                alias='default',
                uuidRepresentation='standard'
            )
            print("✅ MongoEngine connected")
        except Exception as e:
            print(f"⚠️  MongoEngine connection error: {e}")
            print("💡 Tip: If your MongoDB password has special characters, URL encode them")
            raise
        
        # 4. MongoDB - Motor (for dynamic collections)
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        mongodb = mongo_client[MONGO_DB_NAME]
        print("✅ Motor (async MongoDB) connected")
        
        # 5. Redis Client
        # Handle SSL for rediss:// URLs
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        print("✅ Redis connection established")
        
        print("🎉 All database connections initialized successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

async def close_databases():
    """
    Close all database connections
    Called on application shutdown
    """
    global supabase, redis_client, sql_engine, mongo_client
    
    print("\n🛑 Closing database connections...")
    
    try:
        # Close Redis
        if redis_client:
            await redis_client.close()
            print("✅ Redis connection closed")
        
        # Close SQLAlchemy engine
        if sql_engine:
            sql_engine.dispose()
            print("✅ PostgreSQL connection closed")
        
        # Close MongoEngine
        disconnect(alias='default')
        print("✅ MongoEngine disconnected")
        
        # Close Motor
        if mongo_client:
            mongo_client.close()
            print("✅ Motor connection closed")
        
        # Supabase client (no explicit close needed)
        supabase = None
        print("✅ Supabase client cleaned up")
        
        print("👋 All database connections closed successfully")
        
    except Exception as e:
        print(f"⚠️  Error during database cleanup: {e}")

# ============================================================================
# DEPENDENCY INJECTION HELPERS
# ============================================================================

def get_supabase() -> Client:
    """Get Supabase client instance"""
    return supabase

def get_supabase_admin() -> Client:
    """Get Supabase admin client instance (service role)"""
    return supabase_admin

def get_redis():
    """Get Redis client instance"""
    return redis_client

def get_db():
    """Get SQLAlchemy session (for PostgreSQL)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongodb():
    """Get Motor database instance (for async MongoDB operations)"""
    return mongodb

def get_mongodb_sync():
    """Get PyMongo database instance (for sync operations like GridFS)"""
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]