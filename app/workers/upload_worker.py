"""
Upload Worker
Celery worker for processing upload jobs in background
"""

from celery import Task
from celery.signals import worker_process_init
from datetime import datetime
from typing import Dict, Any
from mongoengine import connect

from app.core.celery_app import celery_app
from app.models.mongo_models import AnalysisDataModel, UploadJobModel, FailedRecordModel
from app.config import MONGO_URI, MONGO_DB_NAME, SUPABASE_DB_URL


@worker_process_init.connect
def init_worker(**kwargs):
    """
    Initialize database connections when worker starts
    """
    print("🔧 Initializing worker database connections...")
    try:
        # Connect to MongoDB with MongoEngine
        connect(
            db=MONGO_DB_NAME,
            host=MONGO_URI,
            alias='default',
            uuidRepresentation='standard'
        )
        print("✅ Worker MongoEngine connected")
        
        # Initialize Motor client for async operations
        from motor.motor_asyncio import AsyncIOMotorClient
        import app.config as config
        config.mongo_client = AsyncIOMotorClient(MONGO_URI)
        config.mongodb = config.mongo_client[MONGO_DB_NAME]
        print("✅ Worker Motor connected")
        
        # Initialize SQLAlchemy engine for PostgreSQL
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        try:
            from sqlalchemy import text
            config.sql_engine = create_engine(
                SUPABASE_DB_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            config.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=config.sql_engine)
            # Test connection
            with config.sql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Worker PostgreSQL connected")
        except Exception as pg_error:
            print(f"❌ Worker PostgreSQL connection failed: {pg_error}")
            raise
        
    except Exception as e:
        print(f"❌ Worker database connection failed: {e}")
from app.services.schema_analyzer import Schema, FieldInfo
from app.services.schema_registry import SchemaRegistry
from app.services.data_normalizer import DataNormalizer
from app.services.sql_handler import SQLHandler
from app.services.nosql_handler import NoSQLHandler
from app.utils.hash_utils import HashUtils
from app.config import FAILED_RECORDS_TTL_DAYS


class UploadTask(Task):
    """
    Custom task class with error handling
    """
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure
        """
        job_id = args[0] if args else None
        if job_id:
            try:
                job = UploadJobModel.objects(job_id=job_id).first()
                if job:
                    job.status = 'failed'
                    job.error_message = str(exc)
                    job.error_details = {'traceback': str(einfo)}
                    job.updated_at = datetime.utcnow()
                    job.save()
            except Exception as e:
                print(f"Error updating job status on failure: {e}")


@celery_app.task(
    bind=True,
    base=UploadTask,
    name='app.workers.upload_worker.process_upload_task',
    max_retries=3,
    default_retry_delay=60
)
def process_upload_task(
    self,
    job_id: str,
    analysis_id: str,
    decisions: Dict[str, Dict[str, Any]],
    user_id: str = None
):
    """
    Background task to process upload
    
    Args:
        self: Task instance (bound)
        job_id: Job ID
        analysis_id: Analysis ID
        decisions: User decisions for each schema
        user_id: User ID
    """
    try:
        print(f"🚀 Starting upload job: {job_id}")
        
        # Update job status
        job = UploadJobModel.objects(job_id=job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = 'processing'
        job.progress_stage = 'initializing'
        job.updated_at = datetime.utcnow()
        job.save()
        
        # Retrieve analysis data
        analysis_data = AnalysisDataModel.objects(analysis_id=analysis_id).first()
        if not analysis_data:
            raise ValueError(f"Analysis {analysis_id} not found or expired")
        
        # Initialize services
        schema_registry = SchemaRegistry()
        data_normalizer = DataNormalizer()
        sql_handler = SQLHandler()
        nosql_handler = NoSQLHandler()
        
        entities_created = []
        total_successful = 0
        total_failed = 0
        
        # Process each schema
        for idx, schema_detection in enumerate(analysis_data.schemas_detected):
            schema_id = schema_detection['schema_id']
            decision = decisions.get(schema_id, {})
            
            # Get parsed data for this schema
            schema_data = analysis_data.parsed_data.get(schema_id, [])
            
            if not schema_data:
                continue
            
            # Update progress
            progress_pct = (idx / len(analysis_data.schemas_detected)) * 100
            job.progress_percentage = progress_pct
            job.progress_current = idx * len(schema_data)
            job.save()
            
            # Determine action
            action = decision.get('action', 'create')
            custom_name = decision.get('custom_name')
            entity_name = custom_name or schema_detection['suggested_name']
            storage_type = schema_detection['storage_recommendation']
            
            # Update progress stage
            job.progress_stage = f'processing_{entity_name}'
            job.save()
            
            print(f"📊 Processing schema: {entity_name} ({storage_type})")
            
            # Reconstruct schema object
            schema_fields = {}
            for field_name, field_type in schema_detection['fields'].items():
                schema_fields[field_name] = FieldInfo(
                    name=field_name,
                    type=field_type,
                    nullable=True,
                    sample_values=[],
                    cardinality=0.0,
                    type_distribution={}
                )
            
            schema = Schema(
                schema_id=schema_id,
                fields=schema_fields,
                field_names=set(schema_detection['fields'].keys()),
                record_count=len(schema_data),
                schema_hash=HashUtils.generate_schema_hash(schema_detection['fields']),
                has_nested_objects=False,
                has_arrays=False
            )
            
            # Normalize data
            if storage_type == 'sql':
                norm_result = data_normalizer.prepare_for_sql(schema_data, schema)
            else:
                norm_result = data_normalizer.prepare_for_nosql(schema_data, schema)
            
            print(f"✅ Normalized {norm_result.success_count} records")
            
            # Create storage and insert data
            if storage_type == 'sql':
                # Create table
                success = sql_handler.create_table(
                    table_name=entity_name,
                    schema=schema,
                    indexes=[]
                )
                
                if success:
                    # Insert data
                    insert_result = sql_handler.insert_data(
                        table_name=entity_name,
                        data=norm_result.normalized_data
                    )
                    
                    total_successful += insert_result.success_count
                    total_failed += len(insert_result.failed_records)
                    
                    # Store failed records
                    _store_failed_records(
                        job_id=job_id,
                        entity_name=entity_name,
                        failed_records=insert_result.failed_records
                    )
                    
                    # Store in registry
                    storage_location = f"postgres.public.{entity_name}"
                    schema_registry.create_schema(
                        schema=schema,
                        schema_name=entity_name,
                        storage_type='sql',
                        storage_location=storage_location,
                        user_id=user_id
                    )
                    
                    entities_created.append({
                        'name': entity_name,
                        'storage_type': 'sql',
                        'record_count': insert_result.success_count
                    })
                    
                    print(f"✅ Created SQL table: {entity_name}")
            
            else:  # NoSQL
                # Create collection (async)
                import asyncio
                from motor.motor_asyncio import AsyncIOMotorClient
                
                async def create_and_insert():
                    # Create Motor client in this event loop
                    motor_client = AsyncIOMotorClient(MONGO_URI)
                    motor_db = motor_client[MONGO_DB_NAME]
                    
                    # Create a new NoSQLHandler with this Motor client
                    from app.services.nosql_handler import NoSQLHandler
                    temp_handler = NoSQLHandler.__new__(NoSQLHandler)
                    temp_handler.db = motor_db
                    
                    success = await temp_handler.create_collection(
                        collection_name=entity_name,
                        schema=schema,
                        indexes=[]
                    )
                    
                    if success:
                        insert_result = await temp_handler.insert_documents(
                            collection_name=entity_name,
                            documents=norm_result.normalized_data
                        )
                        motor_client.close()
                        return insert_result
                    
                    motor_client.close()
                    return None
                
                # Run async function - get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                insert_result = loop.run_until_complete(create_and_insert())
                
                if insert_result:
                    total_successful += insert_result.success_count
                    total_failed += len(insert_result.failed_records)
                    
                    # Store failed records
                    _store_failed_records(
                        job_id=job_id,
                        entity_name=entity_name,
                        failed_records=insert_result.failed_records
                    )
                    
                    # Store in registry
                    storage_location = f"mongodb.smart_storage.{entity_name}"
                    schema_registry.create_schema(
                        schema=schema,
                        schema_name=entity_name,
                        storage_type='nosql',
                        storage_location=storage_location,
                        user_id=user_id
                    )
                    
                    entities_created.append({
                        'name': entity_name,
                        'storage_type': 'nosql',
                        'record_count': insert_result.success_count
                    })
                    
                    print(f"✅ Created NoSQL collection: {entity_name}")
        
        # Update job with final results
        job.status = 'completed' if total_failed == 0 else 'completed_with_errors'
        job.entities_created = entities_created
        job.total_records = analysis_data.total_records
        job.successful_records = total_successful
        job.failed_records = total_failed
        job.success_rate = (total_successful / analysis_data.total_records * 100) if analysis_data.total_records > 0 else 0
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.progress_current = analysis_data.total_records
        job.progress_percentage = 100.0
        job.progress_stage = 'completed'
        job.save()
        
        print(f"✅ Upload job completed: {job_id}")
        print(f"   Entities created: {len(entities_created)}")
        print(f"   Records: {total_successful} successful, {total_failed} failed")
        
        return {
            'job_id': job_id,
            'status': job.status,
            'entities_created': entities_created,
            'total_records': analysis_data.total_records,
            'successful': total_successful,
            'failed': total_failed
        }
        
    except Exception as e:
        print(f"❌ Upload job failed: {job_id} - {str(e)}")
        
        # Update job with error
        try:
            job = UploadJobModel.objects(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.updated_at = datetime.utcnow()
                job.save()
        except Exception as update_error:
            print(f"Error updating job status: {update_error}")
        
        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        raise


def _store_failed_records(
    job_id: str,
    entity_name: str,
    failed_records: list
):
    """
    Store failed records in MongoDB with TTL
    
    Args:
        job_id: Job ID
        entity_name: Entity name
        failed_records: List of failed records
    """
    try:
        from datetime import timedelta
        
        expires_at = datetime.utcnow() + timedelta(days=FAILED_RECORDS_TTL_DAYS)
        
        for failed in failed_records:
            record = FailedRecordModel(
                upload_job_id=job_id,
                entity_name=entity_name,
                failed_at=datetime.utcnow(),
                expires_at=expires_at,
                error_type='insertion_error',
                error_message=failed.get('error', 'Unknown error'),
                original_data=failed.get('data', {}),
                row_number=failed.get('row_number', 0)
            )
            record.save()
        
        print(f"📝 Stored {len(failed_records)} failed records")
        
    except Exception as e:
        print(f"Error storing failed records: {e}")
