"""
MongoEngine Models
Defines MongoDB document models for schema registry and related collections
"""

from mongoengine import (
    Document,
    StringField,
    IntField,
    FloatField,
    DictField,
    ListField,
    DateTimeField,
    BooleanField
)
from datetime import datetime


class SchemaRegistryModel(Document):
    """
    Schema Registry Document
    Stores metadata about all schemas in the system
    """
    
    # Identification
    schema_id = StringField(required=True, primary_key=True)
    schema_name = StringField(required=True)
    schema_hash = StringField(required=True, index=True)
    
    # Storage Information
    storage_type = StringField(required=True, choices=['sql', 'nosql'])
    storage_location = StringField(required=True)  # e.g., "postgres.public.users" or "mongodb.smart_storage.users"
    
    # Schema Definition
    fields = DictField(required=True)  # {field_name: {type, nullable, indexed}}
    core_fields = ListField(StringField())  # Non-nullable fields
    optional_fields = ListField(StringField())  # Nullable fields
    
    # Metadata
    version = IntField(default=1)
    record_count = IntField(default=0)
    indexes = ListField(StringField())
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    # Additional Info
    created_by = StringField()  # User ID who created this schema
    description = StringField()
    tags = ListField(StringField())
    
    meta = {
        'collection': 'schema_registry',
        'auto_create_index': False,
        'indexes': [
            'schema_hash',
            'schema_name',
            'storage_type',
            'created_at',
            {'fields': ['schema_name', 'version'], 'unique': True}
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'schema_id': self.schema_id,
            'schema_name': self.schema_name,
            'schema_hash': self.schema_hash,
            'storage_type': self.storage_type,
            'storage_location': self.storage_location,
            'fields': self.fields,
            'core_fields': self.core_fields,
            'optional_fields': self.optional_fields,
            'version': self.version,
            'record_count': self.record_count,
            'indexes': self.indexes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'description': self.description,
            'tags': self.tags
        }


class FailedRecordModel(Document):
    """
    Failed Records Document
    Stores records that failed to insert with TTL
    """
    
    # Identification
    upload_job_id = StringField(required=True, index=True)
    entity_name = StringField(required=True)
    
    # Timestamps
    failed_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(required=True, index=True)  # TTL index
    
    # Error Information
    error_type = StringField(required=True)
    error_message = StringField(required=True)
    
    # Data
    original_data = DictField(required=True)
    row_number = IntField()
    
    meta = {
        'collection': 'failed_records',
        'auto_create_index': False,
        'indexes': [
            'upload_job_id',
            'entity_name',
            {'fields': ['expires_at'], 'expireAfterSeconds': 0}  # TTL index
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'upload_job_id': self.upload_job_id,
            'entity_name': self.entity_name,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'original_data': self.original_data,
            'row_number': self.row_number
        }


class UploadJobModel(Document):
    """
    Upload Job Document
    Tracks background job status and progress
    """
    
    # Identification
    job_id = StringField(required=True, primary_key=True)
    analysis_id = StringField()
    
    # Status
    status = StringField(
        required=True,
        choices=['queued', 'processing', 'completed', 'failed', 'completed_with_errors'],
        default='queued'
    )
    
    # Progress
    progress_current = IntField(default=0)
    progress_total = IntField(default=0)
    progress_percentage = FloatField(default=0.0)
    progress_stage = StringField(default='initializing')
    
    # Results
    entities_created = ListField(DictField())  # [{name, storage_type, record_count}]
    total_records = IntField(default=0)
    successful_records = IntField(default=0)
    failed_records = IntField(default=0)
    success_rate = FloatField(default=0.0)
    
    # Error Information
    error_message = StringField()
    error_details = DictField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    # User Information
    user_id = StringField()
    
    meta = {
        'collection': 'upload_jobs',
        'auto_create_index': False,
        'indexes': [
            'job_id',
            'status',
            'created_at',
            'user_id'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'analysis_id': self.analysis_id,
            'status': self.status,
            'progress': {
                'current': self.progress_current,
                'total': self.progress_total,
                'percentage': self.progress_percentage,
                'stage': self.progress_stage
            } if self.progress_total > 0 else None,
            'result': {
                'entities_created': self.entities_created,
                'total_records': self.total_records,
                'successful': self.successful_records,
                'failed': self.failed_records,
                'success_rate': self.success_rate
            } if self.status in ['completed', 'completed_with_errors'] else None,
            'error': self.error_message if self.status == 'failed' else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'failed_records_url': f"/api/data/upload/{self.job_id}/failed" if self.failed_records > 0 else None
        }


class AnalysisDataModel(Document):
    """
    Analysis Data Document
    Stores temporary analysis data in MongoDB (instead of Redis for persistence)
    """
    
    # Identification
    analysis_id = StringField(required=True, primary_key=True)
    
    # Analysis Results
    schemas_detected = ListField(DictField())
    total_records = IntField()
    files_analyzed = IntField()
    merged_schema = DictField()  # Merged schema for high variance cases
    
    # Parsed Data (stored temporarily)
    parsed_data = DictField()  # {schema_id: [objects]}
    
    # Metadata
    file_names = ListField(StringField())
    user_id = StringField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(required=True, index=True)  # TTL index
    
    meta = {
        'collection': 'analysis_data',
        'auto_create_index': False,
        'indexes': [
            'analysis_id',
            {'fields': ['expires_at'], 'expireAfterSeconds': 0}  # TTL index
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'analysis_id': self.analysis_id,
            'schemas_detected': self.schemas_detected,
            'total_records': self.total_records,
            'files_analyzed': self.files_analyzed,
            'file_names': self.file_names,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class MediaUploadJobModel(Document):
    """
    Media Upload Job Document
    Tracks background media upload job status and progress
    """
    
    # Identification
    job_id = StringField(required=True, primary_key=True)
    user_id = StringField(required=True, index=True)
    
    # Status
    status = StringField(
        required=True,
        choices=['queued', 'processing', 'completed', 'failed', 'completed_with_errors'],
        default='queued'
    )
    
    # Progress
    progress_current = IntField(default=0)
    progress_total = IntField(default=0)
    progress_percentage = FloatField(default=0.0)
    progress_stage = StringField(default='queued')  # queued, uploading, processing_metadata, completed
    
    # Files tracking
    total_files = IntField(default=0)
    uploaded_files = ListField(DictField())  # [{filename, url, public_url, size, content_type, metadata}]
    failed_files = ListField(DictField())  # [{filename, error}]
    
    # Error information
    error_message = StringField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'media_upload_jobs',
        'auto_create_index': False,
        'indexes': [
            'job_id',
            'user_id',
            'status',
            'created_at'
        ]
    }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'status': self.status,
            'progress': {
                'current': self.progress_current,
                'total': self.progress_total,
                'percentage': self.progress_percentage,
                'stage': self.progress_stage
            } if self.progress_total > 0 else None,
            'uploaded_files': self.uploaded_files,
            'failed_files': self.failed_files,
            'error_message': self.error_message if self.status == 'failed' else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
