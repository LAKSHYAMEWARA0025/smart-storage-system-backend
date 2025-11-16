# Smart Storage System Backend

An intelligent multi-modal storage system that automatically analyzes JSON data and determines the optimal storage strategy (SQL or NoSQL) based on data structure and characteristics.

## 🌟 Features

- **Intelligent Storage Decision**: Automatically determines whether data should be stored in SQL (PostgreSQL) or NoSQL (MongoDB)
- **Schema Analysis**: Detects schemas, calculates metrics, and identifies conflicts
- **Unified Query Interface**: Query both SQL and NoSQL data using MongoDB-style syntax
- **Background Processing**: Asynchronous upload processing with Celery
- **Schema Versioning**: Track and evolve schemas over time
- **Conflict Detection**: Identifies similar schemas and prompts for user decisions
- **Progress Tracking**: Real-time job progress monitoring
- **Error Handling**: Failed records tracked and retrievable
- **Authentication**: JWT-based authentication with Supabase
- **Media Storage**: Integrated media file handling with Supabase Storage

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
├─────────────────────────────────────────────────────────────┤
│  • Authentication (JWT)                                      │
│  • File Upload (Media + JSON)                               │
│  • Schema Analysis                                           │
│  • Storage Decision Engine                                   │
│  • Query Interface                                           │
│  • Entity Management                                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Background Workers (Celery)                 │
├─────────────────────────────────────────────────────────────┤
│  • Async upload processing                                   │
│  • Data normalization                                        │
│  • Storage creation                                          │
│  • Progress tracking                                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────┬──────────────────┬──────────────────────┐
│   PostgreSQL     │     MongoDB      │       Redis          │
│   (Supabase)     │                  │                      │
├──────────────────┼──────────────────┼──────────────────────┤
│ • User data      │ • Schema registry│ • Cache              │
│ • SQL tables     │ • NoSQL data     │ • Task queue         │
│                  │ • Job tracking   │ • Temp storage       │
└──────────────────┴──────────────────┴──────────────────────┘
```

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL (via Supabase)
- MongoDB
- Redis

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd smart-storage-system-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
```

Required environment variables:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_DB_URL=postgresql://postgres:password@host:5432/postgres

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=smart_storage

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 3. Run the Application

**Terminal 1 - API Server:**
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

### 4. Access the API

- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/

## 📚 API Documentation

### Authentication

#### Signup
```bash
POST /auth/signup
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Login
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

### Data Upload

#### Analyze JSON Files
```bash
POST /api/data/upload/analyze
Headers: Authorization: Bearer <token>
Body: multipart/form-data
  - files: JSON file(s)
```

#### Execute Upload
```bash
POST /api/data/upload/execute
Headers: Authorization: Bearer <token>
Body: {
  "analysis_id": "xyz-789",
  "decisions": {
    "schema_id": {
      "action": "create",
      "custom_name": "users"
    }
  }
}
```

#### Check Job Status
```bash
GET /api/data/upload/status/{job_id}
Headers: Authorization: Bearer <token>
```

### Query Data

#### Query Any Entity
```bash
POST /api/data/query
Headers: Authorization: Bearer <token>
Body: {
  "entity": "users",
  "filters": {"age": {"$gt": 25}},
  "sort": {"name": 1},
  "limit": 50,
  "offset": 0,
  "fields": ["id", "name", "email"]
}
```

### Entity Management

#### List Entities
```bash
GET /api/data/entities
Headers: Authorization: Bearer <token>
```

#### Get Entity Schema
```bash
GET /api/data/entities/{entity_name}/schema
Headers: Authorization: Bearer <token>
```

#### Get Entity Stats
```bash
GET /api/data/entities/{entity_name}/stats
Headers: Authorization: Bearer <token>
```

## 🎯 SQL Storage Rules

Data is stored in SQL (PostgreSQL) if it passes ALL of these rules:

1. **No Nested Structures**: Data must be flat (no nested objects or arrays)
2. **Null Density ≤ 20%**: Missing values must be minimal
3. **Schema Variants ≤ sqrt(N)**: Limited schema variations
4. **Type Consistency ≥ 90%**: Data types must be consistent

Otherwise, data is stored in NoSQL (MongoDB).

See [docs/SQL_STORAGE_RULES.md](docs/SQL_STORAGE_RULES.md) for detailed rules and examples.

## 🔍 Query Syntax

The system uses MongoDB-style query syntax for both SQL and NoSQL:

```json
{
  "entity": "users",
  "filters": {
    "$and": [
      {"age": {"$gt": 25}},
      {"status": "active"}
    ]
  },
  "sort": {"created_at": -1},
  "limit": 100
}
```

**Supported Operators:**
- Comparison: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`
- Logical: `$and`, `$or`, `$not`
- Array: `$in`, `$nin`
- String: `$regex`, `$contains`
- Existence: `$exists`

## 📁 Project Structure

```
smart-storage-backend/
├── app/
│   ├── api/                    # API routes
│   │   ├── health.py
│   │   ├── upload.py
│   │   ├── query.py
│   │   └── entities.py
│   ├── controllers/            # Business logic
│   │   ├── auth_controller.py
│   │   ├── file_controller.py
│   │   ├── upload_controller.py
│   │   ├── query_controller.py
│   │   └── entities_controller.py
│   ├── services/               # Core services
│   │   ├── schema_analyzer.py
│   │   ├── storage_decision.py
│   │   ├── schema_registry.py
│   │   ├── data_normalizer.py
│   │   ├── sql_handler.py
│   │   ├── nosql_handler.py
│   │   └── naming_service.py
│   ├── workers/                # Celery workers
│   │   └── upload_worker.py
│   ├── models/                 # Data models
│   │   ├── auth_model.py
│   │   ├── file_model.py
│   │   ├── upload_models.py
│   │   ├── query_models.py
│   │   └── mongo_models.py
│   ├── utils/                  # Utilities
│   │   ├── file_parser.py
│   │   ├── metrics.py
│   │   ├── hash_utils.py
│   │   └── query_translator.py
│   ├── core/                   # Core configuration
│   │   ├── celery_app.py
│   │   └── database.py
│   ├── config.py               # Configuration
│   ├── security.py             # Authentication
│   └── main.py                 # Application entry
├── docs/
│   └── SQL_STORAGE_RULES.md    # Storage rules documentation
├── run_celery_worker.py        # Worker startup script
├── celery_monitor.py           # Monitoring tool
├── requirements.txt            # Dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## 🧪 Testing

### Manual Testing

1. **Test Configuration:**
```bash
python -c "from app.config import *; print('✅ Config OK')"
```

2. **Test Application:**
```bash
uvicorn app.main:app --reload
# Visit http://localhost:8000/docs
```

3. **Test Upload:**
```bash
# Create test file
echo '[{"id": 1, "name": "John", "age": 30}]' > test.json

# Upload (requires auth token)
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.json"
```

4. **Test Query:**
```bash
curl -X POST "http://localhost:8000/api/data/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity": "test", "limit": 10}'
```

### Monitor Celery

```bash
# Check worker status
python celery_monitor.py workers

# Check queue status
python celery_monitor.py queues

# Check everything
python celery_monitor.py all
```

## 🔧 Configuration

### File Size Limits

```env
MAX_MEDIA_FILE_SIZE_MB=50
MAX_DATA_FILE_SIZE_MB=50
MAX_FILES_PER_UPLOAD=10
```

### Storage Decision Thresholds

```env
NULL_DENSITY_THRESHOLD=0.20          # 20%
FIELD_OVERLAP_THRESHOLD=0.70         # 70%
TYPE_CONSISTENCY_THRESHOLD=0.90      # 90%
```

### System Limits

```env
MAX_INDEXES_PER_ENTITY=5
FAILED_RECORDS_TTL_DAYS=7
REDIS_UPLOAD_DATA_TTL=1800           # 30 minutes
```

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Required environment variable not set"
**Solution:** Check your `.env` file and ensure all required variables are set.

### Issue: "Database connection failed"
**Solution:** 
- Verify database credentials
- Check if services are running (MongoDB, Redis)
- Test network connectivity

### Issue: "Celery worker not processing tasks"
**Solution:**
```bash
# Check if worker is running
python celery_monitor.py workers

# Restart worker
# Stop: Ctrl+C
# Start: python run_celery_worker.py
```

### Issue: "Upload stuck in 'queued' status"
**Solution:** Ensure Celery worker is running in a separate terminal.

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/
```

### Registry Statistics
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/data/registry/stats
```

### Worker Status
```bash
python celery_monitor.py
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `NODE_ENV=PROD` in environment
- [ ] Use production database credentials
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Scale Celery workers as needed
- [ ] Use managed Redis (AWS ElastiCache, Redis Cloud)
- [ ] Use connection pooling

### Recommended Setup

- **API Servers:** 2-4 instances (load balanced)
- **Celery Workers:** 4-8 workers (auto-scaling)
- **Redis:** Managed service
- **Monitoring:** Flower for Celery, Prometheus/Grafana for metrics

## 📝 License

[Your License Here]

## 👥 Contributors

[Your Team Here]

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Celery for background task processing
- Supabase for authentication and PostgreSQL
- MongoDB for flexible NoSQL storage

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review [docs/SQL_STORAGE_RULES.md](docs/SQL_STORAGE_RULES.md)
3. Check application logs
4. Open an issue on GitHub

---

**Built with ❤️ using FastAPI, Celery, PostgreSQL, and MongoDB**
