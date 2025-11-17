# App Start
uvicorn app.main:app

# For Development
uvicorn app.main:app --reload

# Celery Worker
celery -A app.core.celery_app worker --loglevel=info --pool=solo 