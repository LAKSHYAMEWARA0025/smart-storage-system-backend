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
                        'null_density': schema.null_density,  # Use per-schema null density
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
            # Convert Decimal and other non-JSON types to serializable formats
            def make_serializable(obj):
                """Convert non-JSON serializable objects"""
                from decimal import Decimal
                if isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_serializable(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                return obj
            
            parsed_data = {}
            for schema in analysis.schemas:
                schema_objects = [
                    obj for obj in all_objects
                    if set(obj.keys()) == schema.field_names
                ]
                # Make all data serializable
                parsed_data[schema.schema_id] = [make_serializable(obj) for obj in schema_objects]
            
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
            
            # Get variance recommendation
            try:
                variance_recommendation = decision_engine.get_variance_recommendation(analysis)
                decision_options = decision_engine.get_decision_options(analysis)
            except Exception as e:
                print(f"Error getting variance recommendation: {e}")
                import traceback
                traceback.print_exc()
                variance_recommendation = {
                    "type": "error",
                    "reason": str(e),
                    "storage_type": "nosql",
                    "allow_override": False,
                    "merge_required": False,
                    "max_collections_allowed": 20,
                    "warnings": []
                }
                decision_options = {}
            
            # Add merged schema to response if available
            merged_schema_info = None
            if analysis.merged_schema:
                merged_decision = decision_engine._decide_for_schema(analysis.merged_schema, analysis)
                merged_schema_info = {
                    'schema_id': analysis.merged_schema.schema_id,
                    'fields': {name: info.type for name, info in analysis.merged_schema.fields.items()},
                    'record_count': analysis.merged_schema.record_count,
                    'storage_recommendation': merged_decision.storage_type,
                    'confidence': merged_decision.confidence,
                    'metrics': {
                        'null_density': analysis.merged_schema.null_density,
                        'schema_variants': analysis.schema_variants,
                        'max_allowed_variants': analysis.max_allowed_variants,
                        'type_consistency': merged_decision.metrics.get('type_consistency', 100.0)
                    },
                    'suggested_name': f"{file_names[0].split('.')[0]}_merged" if file_names else "data_merged",
                    'reasons': merged_decision.reasons,
                    'warnings': variance_recommendation.get('warnings', [])
                }
                
                # Add merged schema data to parsed_data
                parsed_data[analysis.merged_schema.schema_id] = [make_serializable(obj) for obj in all_objects]
            
            # Update analysis data with merged schema
            analysis_data.merged_schema = merged_schema_info
            analysis_data.save()
            
            # Check if user decision is required
            requires_decision = (
                any(s.get('conflict') is not None for s in schemas_detected) or
                analysis.variance_level in ["high", "extreme"]
            )
            
            return {
                'analysis_id': analysis_id,
                'files_analyzed': len(files),
                'schemas_detected': schemas_detected,
                'total_records': len(all_objects),
                'schema_variants': analysis.schema_variants,
                'max_allowed_variants': analysis.max_allowed_variants,
                'variance_level': analysis.variance_level,
                'recommendation': variance_recommendation,
                'merged_schema': merged_schema_info,
                'decision_options': decision_options,
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
        user_id: Optional[str] = None,
        user_override: bool = False,
        acknowledge_risks: bool = False
    ) -> Dict[str, Any]:
        """
        Execute upload based on analysis and user decisions
        
        Args:
            analysis_id: Analysis ID from analyze step
            decisions: User decisions for each schema
            user_id: User ID (from auth)
            user_override: Whether user is overriding high variance recommendation
            acknowledge_risks: Whether user acknowledges risks of separate collections
            
        Returns:
            Job information
        """
        from app.config import MAX_COLLECTIONS_PER_UPLOAD
        
        try:
            # Retrieve analysis data
            analysis_data = AnalysisDataModel.objects(analysis_id=analysis_id).first()
            
            if not analysis_data:
                raise HTTPException(
                    status_code=404,
                    detail="Analysis not found or expired"
                )
            
            # Validate number of collections
            num_collections = len(decisions)
            
            if num_collections > MAX_COLLECTIONS_PER_UPLOAD:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot create more than {MAX_COLLECTIONS_PER_UPLOAD} collections per upload. "
                           f"You requested {num_collections}. Please merge schemas or split your upload."
                )
            
            # Check if this is a high variance case requiring override
            schemas_detected = analysis_data.schemas_detected
            schema_variants = len(schemas_detected)
            
            # Reconstruct variance level (simple check)
            is_high_variance = num_collections > 3 and "merged_all" not in decisions
            
            if is_high_variance and num_collections > 1:
                if not user_override:
                    raise HTTPException(
                        status_code=400,
                        detail="High schema variance detected. Set 'user_override: true' to create separate collections, "
                               "or use the merged schema option (schema_id: 'merged_all')."
                    )
                
                if not acknowledge_risks:
                    raise HTTPException(
                        status_code=400,
                        detail="You must set 'acknowledge_risks: true' to confirm you understand that "
                               "separate collections with high variance cannot validate future uploads."
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
