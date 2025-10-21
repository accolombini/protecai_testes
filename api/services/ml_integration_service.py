"""
ML Integration Service
Central coordinator for ML Gateway operations and external ML team integration.

This service orchestrates ML jobs, manages communication with external ML modules,
handles job lifecycle management, and provides comprehensive monitoring.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import HTTPException
import httpx

from api.core.database import get_db
from api.models.ml_models import (
    MLAnalysisJob, MLCoordinationResult, MLSelectivityResult, 
    MLSimulationResult, MLRecommendation, MLDataSnapshot,
    MLJobStatus, MLAnalysisType, MLRecommendationType
)
from api.schemas.ml_schemas import (
    MLJobRequest, MLJobResponse, MLJobStatusResponse, MLHealthResponse,
    MLAnalysisRequest, MLJobSummaryResponse, MLDataRequest
)
from api.services.ml_data_service import MLDataService
from api.services.ml_results_service import MLResultsService
from api.services.etap_service import EtapService


class MLIntegrationService:
    """
    Central service for ML Gateway operations
    Manages job lifecycle, external ML communication, and system coordination
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.data_service = MLDataService(db)
        self.results_service = MLResultsService(db)
        self.etap_service = EtapService(db)
        
        # Configuration for external ML services
        self.ml_service_endpoints = {
            "coordination": "http://ml-coordination-service:8000",
            "selectivity": "http://ml-selectivity-service:8000", 
            "simulation": "http://ml-simulation-service:8000"
        }
        
        # Job monitoring configuration
        self.job_timeout_hours = 24
        self.max_concurrent_jobs = 10
        self.health_check_interval = 300  # 5 minutes
    
    async def create_analysis_job(self, request: MLJobRequest) -> MLJobResponse:
        """
        Create a new ML analysis job
        Main entry point for requesting ML analysis
        """
        try:
            # Validate request
            await self._validate_job_request(request)
            
            # Check concurrent job limits
            await self._check_job_limits()
            
            # Prepare job data
            job_uuid = uuid.uuid4()
            
            # Create job record
            job = MLAnalysisJob(
                uuid=job_uuid,
                job_name=request.job_name,
                job_description=request.job_description,
                analysis_type=MLAnalysisType(request.analysis_type),
                priority=request.priority,
                requested_by=request.requested_by,
                etap_study_ids=request.etap_study_ids,
                equipment_filter=request.equipment_filter,
                analysis_parameters=request.analysis_parameters,
                expected_completion=datetime.now(timezone.utc) + timedelta(hours=self._estimate_job_duration(request)),
                status=MLJobStatus.PENDING,
                processing_logs=[]
            )
            
            # Save job to database
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            
            # Prepare data for ML module
            data_snapshot = await self._prepare_job_data(job, request)
            
            # Update job with data snapshot reference
            job.data_snapshot_uuid = data_snapshot.uuid
            job.total_equipment_count = data_snapshot.total_devices
            job.total_parameter_count = data_snapshot.total_parameters
            self.db.commit()
            
            # Submit job to external ML service (async)
            asyncio.create_task(self._submit_to_ml_service(job, data_snapshot))
            
            return MLJobResponse(
                job_uuid=job.uuid,
                job_name=job.job_name,
                analysis_type=job.analysis_type.value,
                status=job.status.value,
                priority=job.priority,
                created_at=job.created_at,
                expected_completion=job.expected_completion,
                data_snapshot_uuid=data_snapshot.uuid,
                equipment_count=job.total_equipment_count,
                parameter_count=job.total_parameter_count
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating analysis job: {str(e)}"
            )
    
    async def get_job_status(self, job_uuid: uuid.UUID) -> MLJobStatusResponse:
        """
        Get comprehensive status information for a job
        """
        try:
            job = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.uuid == job_uuid
            ).first()
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Calculate progress
            progress_percentage = self._calculate_job_progress(job)
            
            # Get recent logs
            recent_logs = job.processing_logs[-5:] if job.processing_logs else []
            
            # Estimate completion time
            estimated_completion = self._estimate_completion_time(job)
            
            return MLJobStatusResponse(
                job_uuid=job.uuid,
                status=job.status.value,
                progress_percentage=progress_percentage,
                estimated_completion=estimated_completion,
                updated_at=job.updated_at,
                message=recent_logs[-1].get("message", "") if recent_logs else "",
                processing_logs=recent_logs
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting job status: {str(e)}"
            )
    
    async def cancel_job(self, job_uuid: uuid.UUID, reason: Optional[str] = None) -> MLJobStatusResponse:
        """
        Cancel a running ML analysis job
        """
        try:
            job = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.uuid == job_uuid
            ).first()
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            if job.status in [MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot cancel job in {job.status.value} state"
                )
            
            # Update job status
            job.status = MLJobStatus.CANCELLED
            job.updated_at = datetime.now(timezone.utc)
            
            # Add cancellation log
            if not job.processing_logs:
                job.processing_logs = []
            job.processing_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "cancelled",
                "reason": reason or "Manual cancellation",
                "status": "cancelled"
            })
            
            # Notify external ML service of cancellation
            asyncio.create_task(self._notify_ml_service_cancellation(job))
            
            self.db.commit()
            self.db.refresh(job)
            
            return MLJobStatusResponse(
                job_uuid=job.uuid,
                status=job.status.value,
                progress_percentage=0.0,
                estimated_completion=None,
                updated_at=job.updated_at,
                message=f"Job cancelled: {reason or 'Manual cancellation'}"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error cancelling job: {str(e)}"
            )
    
    async def list_jobs(
        self,
        status_filter: Optional[str] = None,
        analysis_type_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MLJobSummaryResponse]:
        """
        List ML analysis jobs with filtering and pagination
        """
        try:
            query = self.db.query(MLAnalysisJob)
            
            if status_filter:
                query = query.filter(MLAnalysisJob.status == MLJobStatus(status_filter))
            
            if analysis_type_filter:
                query = query.filter(MLAnalysisJob.analysis_type == MLAnalysisType(analysis_type_filter))
            
            # Order by creation date (newest first)
            query = query.order_by(desc(MLAnalysisJob.created_at))
            
            # Apply pagination
            jobs = query.offset(offset).limit(limit).all()
            
            job_summaries = []
            for job in jobs:
                # Get result count for this job
                result_count = await self._get_job_result_count(job.uuid)
                
                summary = MLJobSummaryResponse(
                    job_uuid=job.uuid,
                    job_name=job.job_name,
                    analysis_type=job.analysis_type.value,
                    status=job.status.value,
                    priority=job.priority,
                    requested_by=job.requested_by,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    equipment_count=job.total_equipment_count,
                    parameter_count=job.total_parameter_count,
                    result_count=result_count,
                    progress_percentage=self._calculate_job_progress(job)
                )
                job_summaries.append(summary)
            
            return job_summaries
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error listing jobs: {str(e)}"
            )
    
    async def get_system_health(self) -> MLHealthResponse:
        """
        Get comprehensive health status of ML Gateway system
        """
        try:
            # Get job statistics
            total_jobs = self.db.query(MLAnalysisJob).count()
            running_jobs = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.status.in_([MLJobStatus.RUNNING, MLJobStatus.PROCESSING])
            ).count()
            completed_jobs = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.status == MLJobStatus.COMPLETED
            ).count()
            failed_jobs = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.status == MLJobStatus.FAILED
            ).count()
            
            # Calculate success rate
            success_rate = (completed_jobs / max(total_jobs, 1)) * 100
            
            # Check external ML service health
            ml_services_health = await self._check_ml_services_health()
            
            # Check database connectivity
            db_health = await self._check_database_health()
            
            # Check data availability
            data_health = await self._check_data_health()
            
            # Overall system status
            system_status = "healthy"
            if failed_jobs > running_jobs or not ml_services_health["all_healthy"]:
                system_status = "degraded"
            if not db_health or success_rate < 50:
                system_status = "unhealthy"
            
            return MLHealthResponse(
                status=system_status,
                timestamp=datetime.now(timezone.utc),
                version="1.0.0",
                uptime_seconds=self._get_system_uptime(),
                total_jobs=total_jobs,
                running_jobs=running_jobs,
                completed_jobs=completed_jobs,
                failed_jobs=failed_jobs,
                success_rate_percentage=success_rate,
                database_connected=db_health,
                external_services=ml_services_health["services"],
                data_snapshots_available=data_health["snapshots_count"],
                last_successful_job=data_health["last_success"]
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting system health: {str(e)}"
            )
    
    async def cleanup_old_jobs(self, days_threshold: int = 30) -> Dict[str, int]:
        """
        Cleanup old completed/failed jobs and associated data
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
            
            # Find jobs to cleanup
            old_jobs = self.db.query(MLAnalysisJob).filter(
                and_(
                    MLAnalysisJob.updated_at < cutoff_date,
                    MLAnalysisJob.status.in_([MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED])
                )
            ).all()
            
            cleanup_stats = {
                "jobs_deleted": 0,
                "results_deleted": 0,
                "recommendations_deleted": 0,
                "snapshots_deleted": 0,
                "files_deleted": 0
            }
            
            for job in old_jobs:
                # Delete associated results
                coord_results = self.db.query(MLCoordinationResult).filter(
                    MLCoordinationResult.job_uuid == job.uuid
                ).all()
                cleanup_stats["results_deleted"] += len(coord_results)
                
                sel_results = self.db.query(MLSelectivityResult).filter(
                    MLSelectivityResult.job_uuid == job.uuid
                ).all()
                cleanup_stats["results_deleted"] += len(sel_results)
                
                sim_results = self.db.query(MLSimulationResult).filter(
                    MLSimulationResult.job_uuid == job.uuid
                ).all()
                cleanup_stats["results_deleted"] += len(sim_results)
                
                # Delete recommendations
                all_result_uuids = ([r.result_uuid for r in coord_results] + 
                                  [r.result_uuid for r in sel_results] + 
                                  [r.result_uuid for r in sim_results])
                
                recommendations = self.db.query(MLRecommendation).filter(
                    MLRecommendation.result_uuid.in_(all_result_uuids)
                ).all()
                cleanup_stats["recommendations_deleted"] += len(recommendations)
                
                # Delete data snapshots
                if job.data_snapshot_uuid:
                    snapshot = self.db.query(MLDataSnapshot).filter(
                        MLDataSnapshot.uuid == job.data_snapshot_uuid
                    ).first()
                    if snapshot:
                        # Delete associated files
                        if snapshot.file_path and Path(snapshot.file_path).exists():
                            Path(snapshot.file_path).unlink()
                            cleanup_stats["files_deleted"] += 1
                        cleanup_stats["snapshots_deleted"] += 1
                
                # Delete all records
                for rec in recommendations:
                    self.db.delete(rec)
                for result in coord_results + sel_results + sim_results:
                    self.db.delete(result)
                if job.data_snapshot_uuid:
                    snapshot = self.db.query(MLDataSnapshot).filter(
                        MLDataSnapshot.uuid == job.data_snapshot_uuid
                    ).first()
                    if snapshot:
                        self.db.delete(snapshot)
                
                self.db.delete(job)
                cleanup_stats["jobs_deleted"] += 1
            
            self.db.commit()
            return cleanup_stats
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error during cleanup: {str(e)}"
            )
    
    # ===== PRIVATE METHODS =====
    
    async def _validate_job_request(self, request: MLJobRequest):
        """Validate job request parameters"""
        if request.analysis_type not in ["coordination", "selectivity", "simulation"]:
            raise ValueError("Invalid analysis type")
        
        if request.priority not in ["low", "medium", "high", "critical"]:
            raise ValueError("Invalid priority level")
        
        # Validate ETAP study IDs exist
        if request.etap_study_ids:
            existing_studies = await self.etap_service.get_studies_by_ids(request.etap_study_ids)
            if len(existing_studies) != len(request.etap_study_ids):
                raise ValueError("Some ETAP study IDs do not exist")
    
    async def _check_job_limits(self):
        """Check if job creation is within limits"""
        running_jobs = self.db.query(MLAnalysisJob).filter(
            MLAnalysisJob.status.in_([MLJobStatus.RUNNING, MLJobStatus.PROCESSING])
        ).count()
        
        if running_jobs >= self.max_concurrent_jobs:
            raise HTTPException(
                status_code=429,
                detail=f"Maximum concurrent jobs limit reached ({self.max_concurrent_jobs})"
            )
    
    async def _prepare_job_data(self, job: MLAnalysisJob, request: MLJobRequest) -> MLDataSnapshot:
        """Prepare data for ML analysis job"""
        data_request = MLDataRequest(
            etap_study_ids=request.etap_study_ids,
            manufacturer_filter=request.equipment_filter.get("manufacturers") if request.equipment_filter else None,
            parameter_types=request.analysis_parameters.get("parameter_types") if request.analysis_parameters else None,
            data_format="json",
            include_metadata=True
        )
        
        data_response = await self.data_service.extract_data_for_ml(data_request)
        
        # Get the snapshot from the response
        snapshot = self.db.query(MLDataSnapshot).filter(
            MLDataSnapshot.uuid == data_response.snapshot_uuid
        ).first()
        
        return snapshot
    
    async def _submit_to_ml_service(self, job: MLAnalysisJob, data_snapshot: MLDataSnapshot):
        """Submit job to external ML service"""
        try:
            # Update job status
            job.status = MLJobStatus.RUNNING
            job.updated_at = datetime.now(timezone.utc)
            
            if not job.processing_logs:
                job.processing_logs = []
            job.processing_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "submitted_to_ml_service",
                "service": self.ml_service_endpoints.get(job.analysis_type.value),
                "status": "running"
            })
            
            self.db.commit()
            
            # In a real implementation, this would make HTTP requests to external ML services
            # For now, we'll simulate the process
            await asyncio.sleep(1)  # Simulate network delay
            
            # Simulate successful submission
            job.processing_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "ml_service_accepted",
                "message": "Job accepted by ML service",
                "status": "processing"
            })
            
            job.status = MLJobStatus.PROCESSING
            self.db.commit()
            
        except Exception as e:
            # Handle submission failure
            job.status = MLJobStatus.FAILED
            job.processing_logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "status": "failed"
            })
            self.db.commit()
    
    async def _notify_ml_service_cancellation(self, job: MLAnalysisJob):
        """Notify external ML service of job cancellation"""
        try:
            # In real implementation, would make HTTP request to cancel job
            await asyncio.sleep(0.1)  # Simulate network call
        except Exception:
            pass  # Don't fail on notification errors
    
    def _estimate_job_duration(self, request: MLJobRequest) -> int:
        """Estimate job duration in hours"""
        base_hours = {
            "coordination": 2,
            "selectivity": 3,
            "simulation": 4
        }
        
        hours = base_hours.get(request.analysis_type, 2)
        
        # Adjust based on equipment count estimate
        if request.etap_study_ids and len(request.etap_study_ids) > 3:
            hours += 1
        
        return hours
    
    def _calculate_job_progress(self, job: MLAnalysisJob) -> float:
        """Calculate job progress percentage"""
        progress_map = {
            MLJobStatus.PENDING: 0.0,
            MLJobStatus.RUNNING: 25.0,
            MLJobStatus.PROCESSING: 60.0,
            MLJobStatus.COMPLETED: 100.0,
            MLJobStatus.FAILED: 0.0,
            MLJobStatus.CANCELLED: 0.0
        }
        return progress_map.get(job.status, 0.0)
    
    def _estimate_completion_time(self, job: MLAnalysisJob) -> Optional[datetime]:
        """Estimate job completion time"""
        if job.status in [MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED]:
            return None
        
        if job.expected_completion:
            return job.expected_completion
        
        # Fallback estimation
        hours_remaining = 2
        return datetime.now(timezone.utc) + timedelta(hours=hours_remaining)
    
    async def _get_job_result_count(self, job_uuid: uuid.UUID) -> int:
        """Get total result count for a job"""
        coord_count = self.db.query(MLCoordinationResult).filter(
            MLCoordinationResult.job_uuid == job_uuid
        ).count()
        
        sel_count = self.db.query(MLSelectivityResult).filter(
            MLSelectivityResult.job_uuid == job_uuid
        ).count()
        
        sim_count = self.db.query(MLSimulationResult).filter(
            MLSimulationResult.job_uuid == job_uuid
        ).count()
        
        return coord_count + sel_count + sim_count
    
    async def _check_ml_services_health(self) -> Dict[str, Any]:
        """Check health of external ML services"""
        services_health = {}
        all_healthy = True
        
        for service_name, endpoint in self.ml_service_endpoints.items():
            try:
                # In real implementation, would make actual health check requests
                # For now, simulate health checks
                await asyncio.sleep(0.01)  # Simulate network call
                services_health[service_name] = {
                    "status": "healthy",
                    "endpoint": endpoint,
                    "response_time_ms": 50
                }
            except Exception:
                services_health[service_name] = {
                    "status": "unhealthy",
                    "endpoint": endpoint,
                    "error": "Connection failed"
                }
                all_healthy = False
        
        return {
            "services": services_health,
            "all_healthy": all_healthy
        }
    
    async def _check_database_health(self) -> bool:
        """Check database connectivity"""
        try:
            self.db.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    async def _check_data_health(self) -> Dict[str, Any]:
        """Check data availability and quality"""
        try:
            snapshots_count = self.db.query(MLDataSnapshot).count()
            
            last_success = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.status == MLJobStatus.COMPLETED
            ).order_by(desc(MLAnalysisJob.updated_at)).first()
            
            return {
                "snapshots_count": snapshots_count,
                "last_success": last_success.updated_at if last_success else None
            }
        except Exception:
            return {
                "snapshots_count": 0,
                "last_success": None
            }
    
    def _get_system_uptime(self) -> float:
        """Get system uptime in seconds"""
        # Simplified uptime calculation
        return 86400.0  # 24 hours