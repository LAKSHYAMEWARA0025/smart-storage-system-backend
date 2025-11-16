# Smart Storage System - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and fill in your actual values:

```env
# Supabase (Get from your Supabase project dashboard)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_DB_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres

# MongoDB (Local or cloud)
MONGO_URI=mongodb://localhost:27017
# OR for MongoDB Atlas:
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Redis (Local or cloud)
REDIS_URL=redis://localhost:6379/0
# OR for Redis Cloud:
# REDIS_URL=redis://username:password@host:port/0
```

### 3. Start the Application

```bash
uvicorn app.main:app --reload
```

Or:
```bash
python app/main.py
```

### 4. Verify Setup

Open your browser and navigate to:
- Health Check: http://localhost:8000/
- API Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

---

## Detailed Setup Instructions

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (via Supabase)
- MongoDB (local or cloud)
- Redis (local or cloud)

### Installing Dependencies

The `requirements.txt` includes all necessary packages:

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Setting Up Supabase

1. Create a Supabase project at https://supabase.com
2. Get your project URL and anon key from Settings > API
3. Get your PostgreSQL connection string from Settings > Database
4. Add these to your `.env` file

### Setting Up MongoDB

**Option 1: Local MongoDB**
```bash
# Install MongoDB locally
# Then start the service
mongod

# Use default connection string
MONGO_URI=mongodb://localhost:27017
```

**Option 2: MongoDB Atlas (Cloud)**
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a cluster
3. Get connection string
4. Add to `.env`:
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

### Setting Up Redis

**Option 1: Local Redis**
```bash
# Install Redis locally
# Then start the service
redis-server

# Use default connection string
REDIS_URL=redis://localhost:6379/0
```

**Option 2: Redis Cloud**
1. Create account at https://redis.com/try-free/
2. Create database
3. Get connection string
4. Add to `.env`

---

## Testing Your Setup

### 1. Test Configuration Loading

```bash
python -c "from app.config import *; print('✅ Configuration loaded successfully')"
```

Expected output:
```
🔧 Loading configuration...
✅ Configuration loaded successfully
📊 Environment: DEV
📊 Max media file size: 50MB
📊 Max data file size: 50MB
```

### 2. Test Application Startup

```bash
uvicorn app.main:app --reload
```

Expected output:
```
============================================================
🚀 Starting Smart Storage System...
============================================================
🚀 Initializing database connections...
✅ Supabase client initialized
✅ PostgreSQL connection established
✅ MongoEngine connected
✅ Motor (async MongoDB) connected
✅ Redis connection established
🎉 All database connections initialized successfully!
✅ Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 3. Test Health Endpoint

In a new terminal:
```bash
curl http://localhost:8000/
```

Or open in browser: http://localhost:8000/

Expected response:
```json
{
  "status": "Running",
  "timestamp": "2024-01-01T12:00:00",
  "server": {
    "os": "Windows",
    "python_version": "3.11.0",
    "memory": {...},
    "cpu": {...}
  }
}
```

### 4. Test Existing Endpoints

**Signup:**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### 5. Test Graceful Shutdown

Press `Ctrl+C` in the terminal running uvicorn.

Expected output:
```
⚠️  Received shutdown signal...
============================================================
🛑 Shutting down Smart Storage System...
============================================================
🛑 Closing database connections...
✅ Redis connection closed
✅ PostgreSQL connection closed
✅ MongoEngine disconnected
✅ Motor connection closed
✅ Supabase client cleaned up
👋 All database connections closed successfully
✅ Application shutdown complete
👋 Goodbye!
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Required environment variable 'X' is not set"

**Solution:** Check your `.env` file and ensure all required variables are set.

Required variables:
- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_DB_URL
- MONGO_URI
- REDIS_URL

### Issue: "Error initializing Supabase client"

**Solution:** 
- Verify SUPABASE_URL and SUPABASE_KEY are correct
- Check your internet connection
- Verify your Supabase project is active

### Issue: "MongoEngine connection failed"

**Solution:**
- Verify MONGO_URI is correct
- Check MongoDB service is running (if local)
- Check network access settings (if cloud)
- Verify credentials

### Issue: "Redis connection failed"

**Solution:**
- Verify REDIS_URL is correct
- Check Redis service is running (if local)
- Check network access settings (if cloud)
- Verify credentials

### Issue: "PostgreSQL connection failed"

**Solution:**
- Verify SUPABASE_DB_URL is correct
- Check connection string format:
  ```
  postgresql://postgres:password@host:5432/postgres
  ```
- Verify database is accessible

---

## Development Workflow

### Running in Development Mode

```bash
# With auto-reload
uvicorn app.main:app --reload

# With custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Running in Production Mode

```bash
# Set environment
export NODE_ENV=PROD  # or set NODE_ENV=PROD on Windows

# Run without reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Viewing Logs

All important events are logged to console:
- Configuration loading
- Database connections
- Startup/shutdown events
- Errors and warnings

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| SUPABASE_URL | Supabase project URL | https://xxx.supabase.co |
| SUPABASE_KEY | Supabase anon key | eyJhbGc... |
| SUPABASE_DB_URL | PostgreSQL connection | postgresql://... |
| MONGO_URI | MongoDB connection | mongodb://localhost:27017 |
| REDIS_URL | Redis connection | redis://localhost:6379/0 |

### Optional Variables (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| NODE_ENV | DEV | Environment mode |
| ALLOWED_ORIGINS | * | CORS allowed origins |
| MONGO_DB_NAME | smart_storage | MongoDB database name |
| REDIS_UPLOAD_DATA_TTL | 1800 | Redis TTL (30 min) |
| MAX_MEDIA_FILE_SIZE_MB | 50 | Max media file size |
| MAX_DATA_FILE_SIZE_MB | 50 | Max data file size |
| MAX_FILES_PER_UPLOAD | 10 | Max files per upload |
| NULL_DENSITY_THRESHOLD | 0.20 | SQL null threshold |
| FIELD_OVERLAP_THRESHOLD | 0.70 | Schema overlap threshold |
| TYPE_CONSISTENCY_THRESHOLD | 0.90 | Type consistency threshold |
| MAX_INDEXES_PER_ENTITY | 5 | Max indexes per table |
| FAILED_RECORDS_TTL_DAYS | 7 | Failed records TTL |

---

## Next Steps

Once your setup is complete and verified:

1. ✅ All dependencies installed
2. ✅ Environment variables configured
3. ✅ Application starts successfully
4. ✅ All database connections working
5. ✅ Health endpoint responds

You're ready to proceed with Phase 2 implementation!

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review `docs/SQL_STORAGE_RULES.md` for system rules
3. Check application logs for detailed error messages

---

**Happy Coding! 🚀**
