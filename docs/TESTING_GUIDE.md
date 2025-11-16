# Complete Testing Guide

This guide will help you test all features and validate that media and structured data are going to the proper databases and collections.

---

## 🚀 Pre-Testing Setup

### 1. Ensure All Services Are Running

**Terminal 1 - FastAPI Server:**
```bash
uvicorn app.main:app --reload
```

**Terminal 2 - Celery Worker:**
```bash
python run_celery_worker.py
```

**Terminal 3 - Monitor (Optional):**
```bash
python celery_monitor.py
```

### 2. Verify Services Are Up

```bash
# Check API
curl http://localhost:8000/

# Expected: Health check response with server info
```

---

## 🔐 Step 1: Authentication

### Create Test User

```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Expected Response:**
```json
{
  "message": "Signup successful. Please check your email to verify.",
  "user_id": "uuid-here"
}
```

### Login and Get Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Save this token! You'll need it for all subsequent requests.**

```bash
# Set token as environment variable (easier for testing)
# Windows PowerShell:
$TOKEN = "your-token-here"

# Windows CMD:
set TOKEN=your-token-here

# Linux/Mac:
export TOKEN="your-token-here"
```

---

## 📁 Step 2: Test Media Upload (Supabase Storage)

### Create Test Media Files

**test_image.txt** (simulating an image):
```
This is a test image file
```

**test_video.txt** (simulating a video):
```
This is a test video file
```

### Upload Media File

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_image.txt"
```

**Expected Response:**
```json
{
  "user_id": "uuid",
  "filename": "test_image.txt",
  "url": "https://...supabase.co/storage/v1/...",
  "file_type": "text",
  "extension": ".txt"
}
```

### Verify Media in Supabase

**Option 1: Check via API**
```bash
curl "http://localhost:8000/api/files" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** List of uploaded files

**Option 2: Check Supabase Dashboard**
1. Go to your Supabase project
2. Navigate to Storage → uploads
3. You should see your file under `{user_id}/test_image.txt`

**Option 3: Check PostgreSQL (files table)**
```bash
# Connect to your Supabase PostgreSQL
# Check the 'files' table
SELECT * FROM files WHERE user_id = 'your-user-id';
```

---

## 📊 Step 3: Test Structured Data Upload (Smart Storage)

### Create Test JSON Files

**test_users.json** (SQL-compatible data):
```json
[
  {"id": 1, "name": "John Doe", "email": "john@test.com", "age": 30},
  {"id": 2, "name": "Jane Smith", "email": "jane@test.com", "age": 25},
  {"id": 3, "name": "Bob Johnson", "email": "bob@test.com", "age": 35}
]
```

**test_logs.json** (NoSQL-compatible data - nested):
```json
[
  {
    "timestamp": "2024-01-01T12:00:00Z",
    "level": "info",
    "message": "User logged in",
    "metadata": {
      "ip": "192.168.1.1",
      "browser": "Chrome"
    }
  },
  {
    "timestamp": "2024-01-01T12:05:00Z",
    "level": "error",
    "message": "Database connection failed",
    "metadata": {
      "error_code": 500,
      "retry_count": 3
    }
  }
]
```

**test_products.json** (SQL-compatible):
```json
[
  {"product_id": 1, "name": "Laptop", "price": 999.99, "stock": 50},
  {"product_id": 2, "name": "Mouse", "price": 29.99, "stock": 200},
  {"product_id": 3, "name": "Keyboard", "price": 79.99, "stock": 150}
]
```

### Test 1: Upload SQL-Compatible Data

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_users.json"
```

**Expected Response:**
```json
{
  "message": "JSON data processed and stored successfully",
  "filename": "test_users.json",
  "job_id": "job-123",
  "schemas_detected": 1,
  "total_records": 3
}
```

**What Happens:**
1. System detects it's JSON
2. Routes to smart storage
3. Analyzes schema (flat structure, no nulls)
4. Decides: SQL (PostgreSQL)
5. Creates table `test_users` or `users`
6. Inserts 3 records

### Test 2: Upload NoSQL-Compatible Data

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_logs.json"
```

**Expected Response:**
```json
{
  "message": "JSON data processed and stored successfully",
  "filename": "test_logs.json",
  "job_id": "job-456",
  "schemas_detected": 1,
  "total_records": 2
}
```

**What Happens:**
1. System detects it's JSON
2. Routes to smart storage
3. Analyzes schema (nested objects detected)
4. Decides: NoSQL (MongoDB)
5. Creates collection `test_logs` or `logs`
6. Inserts 2 documents

### Test 3: Check Job Status

```bash
curl "http://localhost:8000/api/data/upload/status/job-123" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "job_id": "job-123",
  "status": "completed",
  "progress": {
    "current": 3,
    "total": 3,
    "percentage": 100.0,
    "stage": "completed"
  },
  "result": {
    "entities_created": [
      {
        "name": "users",
        "storage_type": "sql",
        "record_count": 3
      }
    ],
    "total_records": 3,
    "successful": 3,
    "failed": 0,
    "success_rate": 100.0
  }
}
```

---

## 🔍 Step 4: Verify Data in Databases

### Verify SQL Data (PostgreSQL)

**Option 1: Using API**
```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "users",
    "limit": 10
  }'
```

**Expected Response:**
```json
{
  "entity": "users",
  "storage_type": "sql",
  "returned_count": 3,
  "data": [
    {"id": 1, "name": "John Doe", "email": "john@test.com", "age": 30},
    {"id": 2, "name": "Jane Smith", "email": "jane@test.com", "age": 25},
    {"id": 3, "name": "Bob Johnson", "email": "bob@test.com", "age": 35}
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "has_more": false,
    "total_count": 3
  }
}
```

**Option 2: Direct PostgreSQL Query**
```sql
-- Connect to your Supabase PostgreSQL database
-- List all tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Check users table
SELECT * FROM users;

-- Check table structure
\d users
```

### Verify NoSQL Data (MongoDB)

**Option 1: Using API**
```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "logs",
    "limit": 10
  }'
```

**Expected Response:**
```json
{
  "entity": "logs",
  "storage_type": "nosql",
  "returned_count": 2,
  "data": [
    {
      "_id": "...",
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "info",
      "message": "User logged in",
      "metadata": {
        "ip": "192.168.1.1",
        "browser": "Chrome"
      }
    },
    {
      "_id": "...",
      "timestamp": "2024-01-01T12:05:00Z",
      "level": "error",
      "message": "Database connection failed",
      "metadata": {
        "error_code": 500,
        "retry_count": 3
      }
    }
  ]
}
```

**Option 2: Direct MongoDB Query**
```bash
# Connect to MongoDB
mongosh "your-mongodb-connection-string"

# Switch to database
use smart_storage

# List collections
show collections

# Check logs collection
db.logs.find().pretty()

# Count documents
db.logs.countDocuments()
```

---

## 📋 Step 5: Test Entity Management

### List All Entities

```bash
curl "http://localhost:8000/api/data/entities" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "total_entities": 2,
  "entities": [
    {
      "name": "users",
      "storage_type": "sql",
      "storage_location": "postgres.public.users",
      "record_count": 3,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "version": 1
    },
    {
      "name": "logs",
      "storage_type": "nosql",
      "storage_location": "mongodb.smart_storage.logs",
      "record_count": 2,
      "created_at": "2024-01-01T12:05:00Z",
      "updated_at": "2024-01-01T12:05:00Z",
      "version": 1
    }
  ]
}
```

### Get Entity Schema

```bash
curl "http://localhost:8000/api/data/entities/users/schema" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "entity_name": "users",
  "storage_type": "sql",
  "version": 1,
  "fields": [
    {"name": "id", "type": "integer", "nullable": false, "indexed": true},
    {"name": "name", "type": "string", "nullable": false, "indexed": false},
    {"name": "email", "type": "string", "nullable": false, "indexed": false},
    {"name": "age", "type": "integer", "nullable": true, "indexed": false}
  ],
  "core_fields": ["id", "name", "email"],
  "optional_fields": ["age"],
  "indexes": ["id"]
}
```

### Get Entity Statistics

```bash
curl "http://localhost:8000/api/data/entities/users/stats" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🧪 Step 6: Test Query Features

### Simple Query

```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "users",
    "filters": {"age": {"$gt": 25}},
    "limit": 10
  }'
```

**Expected:** Users with age > 25

### Complex Query with Sort

```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "users",
    "filters": {
      "$and": [
        {"age": {"$gte": 25}},
        {"age": {"$lte": 35}}
      ]
    },
    "sort": {"name": 1},
    "limit": 10
  }'
```

**Expected:** Users aged 25-35, sorted by name

### Query with Projection

```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": "users",
    "fields": ["name", "email"],
    "limit": 10
  }'
```

**Expected:** Only name and email fields returned

---

## ✅ Verification Checklist

### Media Files (Supabase)
- [ ] File uploaded successfully
- [ ] File appears in Supabase Storage
- [ ] Metadata stored in PostgreSQL `files` table
- [ ] File accessible via public URL
- [ ] Can retrieve file list via API

### SQL Data (PostgreSQL)
- [ ] JSON file analyzed correctly
- [ ] Decided as SQL storage
- [ ] Table created in PostgreSQL
- [ ] Data inserted successfully
- [ ] Can query data via API
- [ ] Schema registered in MongoDB
- [ ] Entity appears in entities list

### NoSQL Data (MongoDB)
- [ ] JSON file analyzed correctly
- [ ] Decided as NoSQL storage
- [ ] Collection created in MongoDB
- [ ] Documents inserted successfully
- [ ] Can query data via API
- [ ] Schema registered in MongoDB
- [ ] Entity appears in entities list

### Background Processing
- [ ] Celery worker running
- [ ] Jobs queued successfully
- [ ] Job status updates correctly
- [ ] Progress tracked accurately
- [ ] Completed jobs show results

### Query Interface
- [ ] Can query SQL data
- [ ] Can query NoSQL data
- [ ] Filters work correctly
- [ ] Sort works correctly
- [ ] Pagination works correctly
- [ ] Projection works correctly

---

## 🔍 Detailed Database Verification

### Check PostgreSQL (Supabase)

```sql
-- Connect to Supabase PostgreSQL
-- (Use Supabase dashboard SQL editor or psql)

-- 1. List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. Check files table (media metadata)
SELECT * FROM files 
ORDER BY created_at DESC 
LIMIT 10;

-- 3. Check dynamically created tables
-- (Replace 'users' with your table name)
SELECT * FROM users;

-- 4. Check table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users';

-- 5. Count records
SELECT COUNT(*) FROM users;
```

### Check MongoDB

```javascript
// Connect to MongoDB
// mongosh "your-connection-string"

// 1. Switch to database
use smart_storage

// 2. List all collections
show collections

// 3. Check schema_registry
db.schema_registry.find().pretty()

// 4. Check upload_jobs
db.upload_jobs.find().sort({created_at: -1}).limit(5).pretty()

// 5. Check user data collections
db.logs.find().pretty()

// 6. Count documents
db.logs.countDocuments()

// 7. Check failed_records (should be empty if all succeeded)
db.failed_records.find().pretty()

// 8. Check analysis_data (temporary, may be expired)
db.analysis_data.find().pretty()
```

### Check Redis

```bash
# Connect to Redis
redis-cli

# Check keys
KEYS *

# Check upload data (temporary)
KEYS upload_data:*

# Check Celery tasks
KEYS celery-task-meta-*

# Check cache
KEYS files:*
```

---

## 🐛 Troubleshooting

### Issue: Upload returns 401 Unauthorized
**Solution:** Check your token is valid and included in Authorization header

### Issue: Upload stuck in "queued" status
**Solution:** Ensure Celery worker is running
```bash
python celery_monitor.py workers
```

### Issue: Data not appearing in database
**Solution:** 
1. Check job status for errors
2. Check failed records endpoint
3. Check Celery worker logs

### Issue: Can't query data
**Solution:**
1. Verify entity exists: `GET /api/data/entities`
2. Check entity name matches exactly
3. Verify you have permission (correct user)

---

## 📊 Complete Test Script

Create a file `test_all.sh` (Linux/Mac) or `test_all.ps1` (Windows):

```bash
#!/bin/bash

# Set your token
TOKEN="your-token-here"

echo "Testing Smart Storage System..."

# Test 1: Health Check
echo "\n1. Health Check"
curl http://localhost:8000/

# Test 2: Upload SQL Data
echo "\n2. Uploading SQL-compatible data..."
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_users.json"

# Test 3: Upload NoSQL Data
echo "\n3. Uploading NoSQL-compatible data..."
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_logs.json"

# Wait for processing
echo "\n4. Waiting for processing..."
sleep 5

# Test 4: List Entities
echo "\n5. Listing entities..."
curl "http://localhost:8000/api/data/entities" \
  -H "Authorization: Bearer $TOKEN"

# Test 5: Query SQL Data
echo "\n6. Querying SQL data..."
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity": "users", "limit": 10}'

# Test 6: Query NoSQL Data
echo "\n7. Querying NoSQL data..."
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity": "logs", "limit": 10}'

echo "\n\nAll tests completed!"
```

---

## ✅ Success Criteria

Your system is working correctly if:

1. ✅ Media files go to Supabase Storage
2. ✅ Media metadata goes to PostgreSQL `files` table
3. ✅ SQL-compatible JSON creates PostgreSQL tables
4. ✅ NoSQL-compatible JSON creates MongoDB collections
5. ✅ All schemas registered in MongoDB `schema_registry`
6. ✅ Can query both SQL and NoSQL data via unified API
7. ✅ Entities list shows all created tables/collections
8. ✅ Job status tracking works
9. ✅ Celery worker processes jobs
10. ✅ No errors in logs

---

**Happy Testing! 🚀**
