# Docker Deployment Guide

## Quick Start

### 1. Build and Run
```bash
docker-compose up --build
```

### 2. Run in Background
```bash
docker-compose up -d
```

### 3. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery_worker
```

### 4. Stop Services
```bash
docker-compose down
```

### 5. Stop and Remove Volumes
```bash
docker-compose down -v
```

## Services

- **api** - FastAPI application (http://localhost:8000)
- **celery_worker** - Background task processor
- **redis** - Message broker (optional if using external Redis)

## Environment Variables

Make sure your `.env` file is configured with:

```env
# If using Docker Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# If using external Redis (Upstash)
# REDIS_URL=rediss://your-upstash-url
# CELERY_BROKER_URL=rediss://your-upstash-url
# CELERY_RESULT_BACKEND=rediss://your-upstash-url

# MongoDB
MONGO_URI=mongodb+srv://...
MONGO_DB_NAME=smart_storage

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=...
SUPABASE_DB_URL=postgresql://...
```

## Production Deployment

### Using External Services (Recommended)

If you're using external Redis (Upstash) and MongoDB (Atlas), you can remove the Redis service:

```yaml
# Comment out or remove the redis service in docker-compose.yml
# and remove depends_on: redis from api and celery_worker
```

### Scaling Workers

Scale Celery workers:
```bash
docker-compose up -d --scale celery_worker=3
```

### Health Checks

Check if services are running:
```bash
docker-compose ps
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart celery_worker
```

## Troubleshooting

### View Worker Status
```bash
docker-compose exec celery_worker celery -A app.core.celery_app inspect active
```

### Access Container Shell
```bash
docker-compose exec api bash
docker-compose exec celery_worker bash
```

### Check Redis Connection
```bash
docker-compose exec redis redis-cli ping
```

## Development vs Production

### Development (with hot reload)
```yaml
# In docker-compose.yml, change command to:
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production
Use the default command without `--reload` flag.
