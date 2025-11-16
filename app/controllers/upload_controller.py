"""
Upload Controller
Handles business logic for structured data upload
"""

import json
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime, timedelta

from app.utils.file_parser import FileParser
from app.services.schema_analyzer import SchemaAnalyzer
from app.services.storage_decision import StorageDecisionEngine
from app.services.naming_service import NamingService
from app.services.schema_registry import SchemaRegistry
from app.services.data_normalizer import DataNormalizer
from app.services.sql_handler import SQLHandler
from app.services.nosql_handler import NoSQLHandler
from app.models.mongo_models import AnalysisDataModel, UploadJobModel
from app.utils.hash_utils import HashUtils
from app.config import get_redis, REDIS_UPLOAD_DATA_TTL, MAX_DATA_FILE_SIZE


class UploadController:
    """
    Controller for structured data upload operations
    """
    
    @staticmethod
    async def analyze_upload(
        files: List[UploadFile],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze uploaded files and return schema detection results
        
        Args:
            files: List of uploaded files
            user_id: User ID (from auth)
            metadata: Optional metadata (suggested names, preferences)
            
        Returns:
            Analysis response dictionary
        """
        try:
            # Validate files
            for file in files:
                # Check file size
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(0)  # Reset
                
                if file_size > MAX_DATA_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} exceeds maximum size"
                    )
                
                # Validate JSON
                content = await file.read()
                await file.seek(0)
                is_valid, error = FileParser.validate_json_content(content)
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid JSON in {file.filename}: {error}"
                    )
            
            # Parse all files
            all_objects = []
            file_names = []
            
            for file in files:
                objects = await FileParser.parse_json_to_list(file)
                all_objects.extend(objects)
                file_names.append(file.filename)
            
            if not all_objects:
                raise HTTPException(
                    status_code=400,
                    detail="No data found in uploaded files"
                )
            
            # Analyze schemas
            analyzer = SchemaAnalyzer()
            analysis = analyzer.analyze_objects(all_objects)
            
            # Make storage decisions
            decision_engine = StorageDecisionEngine()
            decisions = decision_engine.decide_storage(analysis)
            
            # Generate names and check for conflicts
            naming_service = NamingService()
            schema_registry = SchemaRegistry()
            
            schemas_detected = []
            
            for schema in analysis.schemas:
                decision = decisions[schema.schema_id]
                
                # Generate name
                suggested_name = naming_service.generate_name(
                    schema=schema,
                    file_name=file_names[0] if file_names else None,
                    user_suggested=metadata.get('suggested_name') if metadata else None
                )
                
                # Check for conflicts
                conflicts = schema_registry.check_for_conflicts(schema, suggested_name)
                
                # Build schema detection response
                schema_detection = {
                    'schema_id': schema.schema_id,
                    'fields': {name: info.type for name, info in schema.fields.items()},
                    'record_count': schema.record_count,
                    'storage_recommendation': decision.storage_type,
                    'confidence': decision.confidence,
                    'metrics': {
                        'null_density': analysis.null_density,
                        'schema_variants': analysis.schema_variants,
                        'max_allowed_variants': analysis.max_allowed_variants,
                        'type_consistency': decision.metrics.get('type_consistency', 100.0)
                    },
                    'conflict': None,
                    'suggested_name': suggested_name,
                    'reasons': decision.reasons
                }
                
                # Add conflict info if exists
                if conflicts['has_conflict']:
                    schema_detection['conflict'] = {
                        'type': conflicts['conflict_type'],
                        'existing_schema': conflicts['existing_schema']['schema_name'] if conflicts['existing_schema'] else None,
                        'similarity': conflicts['similarity'],
                        'impact': f"Similarity: {conflicts['similarity']}%",
                        'options': [
                            {'id': 'evolve', 'label': 'Evolve existing schema'},
                            {'id': 'new_table', 'label': 'Create new table/collection'}
                        ]
                    }
                
                schemas_detected.append(schema_detection)
            
            # Store analysis data temporarily
            analysis_id = HashUtils.generate_analysis_id()
            
            # Prepare parsed data grouped by schema
            parsed_data = {}
            for schema in analysis.schemas:
                schema_objects = [
                    obj for obj in all_objects
                    if set(obj.keys()) == schema.field_names
                ]
                parsed_data[schema.schema_id] = schema_objects
            
            # Store in MongoDB with TTL
            expires_at = datetime.utcnow() + timedelta(seconds=REDIS_UPLOAD_DATA_TTL)
            
            analysis_data = AnalysisDataModel(
                analysis_id=analysis_id,
                schemas_detected=schemas_detected,
                total_records=len(all_objects),
                files_analyzed=len(files),
                parsed_data=parsed_data,
                file_names=file_names,
                user_id=user_id,
                expires_at=expires_at
            )
            analysis_data.save()
            
            # Check if user decision is required
            requires_decision = any(
                s.get('conflict') is not None for s in schemas_detected
            )
            
            return {
                'analysis_id': analysis_id,
                'files_analyzed': len(files),
                'schemas_detected': schemas_detected,
                'total_records': len(all_objects),
                'requires_decision': requires_decision
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {str(e)}"
            )
    
    @staticmethod
    async def execute_upload(
        analysis_id: str,
        decisions: Dict[str, Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute upload based on analysis and user decisions
        
        Args:
            analysis_id: Analysis ID from analyze step
            decisions: User decisions for each schema
            user_id: User ID (from auth)
            
        Returns:
            Job information
        """
        try:
            # Retrieve analysis data
            analysis_data = AnalysisDataModel.objects(analysis_id=analysis_id).first()
            
            if not analysis_data:
                raise HTTPException(
                    status_code=404,
                    detail="Analysis not found or expired"
                )
            
            # Create upload job
            job_id = HashUtils.generate_job_id()
            
            job = UploadJobModel(
                job_id=job_id,
                analysis_id=analysis_id,
                status='queued',
                progress_total=analysis_data.total_records,
                user_id=user_id
            )
            job.save()
            
            # Queue background task with Celery
            from app.workers.upload_worker import process_upload_task
            
            # Convert Pydantic models to dicts for JSON serialization
            decisions_dict = {
                schema_id: decision.model_dump() if hasattr(decision, 'model_dump') else decision
                for schema_id, decision in decisions.items()
            }
            
            process_upload_task.delay(
                job_id=job_id,
                analysis_id=analysis_id,
                decisions=decisions_dict,
                user_id=user_id
            )
            
            return {
                'job_id': job_id,
                'status': 'processing',
                'message': 'Upload is being processed'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload execution failed: {str(e)}"
            )
    
    @staticmethod
    async def _process_upload(
        job_id: str,
        analysis_data: AnalysisDataModel,
        decisions: Dict[str, Dict[str, Any]],
        user_id: Optional[str] = None
    ):
        """
        Process upload (will be moved to Celery worker in Phase 7)
        
        Args:
            job_id: Job ID
            analysis_data: Analysis data from MongoDB
            decisions: User decisions
            user_id: User ID
        """
        try:
            # Update job status
            job = UploadJobModel.objects(job_id=job_id).first()
            job.status = 'processing'
            job.progress_stage = 'initializing'
            job.save()
            
            # Initialize services
            schema_registry = SchemaRegistry()
            data_normalizer = DataNormalizer()
            sql_handler = SQLHandler()
            nosql_handler = NoSQLHandler()
            
            entities_created = []
            total_successful = 0
            total_failed = 0
            
            # Process each schema
            for schema_detection in analysis_data.schemas_detected:
                schema_id = schema_detection['schema_id']
                decision = decisions.get(schema_id, {})
                
                # Get parsed data for this schema
                schema_data = analysis_data.parsed_data.get(schema_id, [])
                
                if not schema_data:
                    continue
                
                # Determine action
                action = decision.get('action', 'create')
                custom_name = decision.get('custom_name')
                entity_name = custom_name or schema_detection['suggested_name']
                storage_type = schema_detection['storage_recommendation']
                
                # Update progress
                job.progress_stage = f'processing_{entity_name}'
                job.save()
                
                # Reconstruct schema object (simplified)
                from app.services.schema_analyzer import Schema, FieldInfo
                
                schema_fields = {}
                for field_name, field_type in schema_detection['fields'].items():
                    schema_fields[field_name] = FieldInfo(
                        name=field_name,
                        type=field_type,
                        nullable=True,  # Simplified
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
                
                # Create storage
                if storage_type == 'sql':
                    # Create table
                    success = sql_handler.create_table(
                        table_name=entity_name,
                        schema=schema,
                        indexes=[]  # Will add indexes later
                    )
                    
                    if success:
                        # Insert data
                        insert_result = sql_handler.insert_data(
                            table_name=entity_name,
                            data=norm_result.normalized_data
                        )
                        
                        total_successful += insert_result.success_count
                        total_failed += len(insert_result.failed_records)
                        
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
                
                else:  # NoSQL
                    # Create collection
                    success = await nosql_handler.create_collection(
                        collection_name=entity_name,
                        schema=schema,
                        indexes=[]
                    )
                    
                    if success:
                        # Insert documents
                        insert_result = await nosql_handler.insert_documents(
                            collection_name=entity_name,
                            documents=norm_result.normalized_data
                        )
                        
                        total_successful += insert_result.success_count
                        total_failed += len(insert_result.failed_records)
                        
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
            
            # Update job with results
            job.status = 'completed' if total_failed == 0 else 'completed_with_errors'
            job.entities_created = entities_created
            job.total_records = analysis_data.total_records
            job.successful_records = total_successful
            job.failed_records = total_failed
            job.success_rate = (total_successful / analysis_data.total_records * 100) if analysis_data.total_records > 0 else 0
            job.completed_at = datetime.utcnow()
            job.progress_current = analysis_data.total_records
            job.progress_percentage = 100.0
            job.progress_stage = 'completed'
            job.save()
            
        except Exception as e:
            # Update job with error
            job = UploadJobModel.objects(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.save()
            raise
    
    @staticmethod
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """
        Get upload job status
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status information
        """
        try:
            job = UploadJobModel.objects(job_id=job_id).first()
            
            if not job:
                raise HTTPException(
                    status_code=404,
                    detail="Job not found"
                )
            
            return job.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get job status: {str(e)}"
            )
