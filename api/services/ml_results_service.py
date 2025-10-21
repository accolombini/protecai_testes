"""
ML Results Service
Handles results submission and management for external ML modules.

This service processes ML analysis results, validation, storage,
and provides feedback mechanisms for ML model performance tracking.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import HTTPException
import pandas as pd

from api.core.database import get_db
from api.models.ml_models import (
    MLAnalysisJob, MLCoordinationResult, MLSelectivityResult, 
    MLSimulationResult, MLRecommendation, MLDataSnapshot,
    MLJobStatus, MLAnalysisType, MLRecommendationType
)
from api.schemas.ml_schemas import (
    MLCoordinationResultRequest, MLSelectivityResultRequest,
    MLSimulationResultRequest, MLRecommendationRequest,
    MLResultResponse, MLJobStatusResponse, MLRecommendationResponse
)


class MLResultsService:
    """
    Service for handling ML analysis results from external ML modules
    Manages result validation, storage, and performance tracking
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.results_path = Path("outputs/ml_results")
        self.results_path.mkdir(parents=True, exist_ok=True)
    
    async def submit_coordination_result(
        self, 
        job_uuid: uuid.UUID, 
        result: MLCoordinationResultRequest
    ) -> MLResultResponse:
        """
        Submit coordination analysis results from ML module
        """
        try:
            # Validate job exists and is in correct state
            job = await self._validate_job_for_results(job_uuid, MLAnalysisType.COORDINATION)
            
            # Validate result data
            await self._validate_coordination_result(result)
            
            # Create result record
            ml_result = MLCoordinationResult(
                job_uuid=job.uuid,
                result_uuid=uuid.uuid4(),
                analysis_type=MLAnalysisType.COORDINATION,
                status="completed",
                confidence_score=result.confidence_score,
                analysis_summary=result.analysis_summary,
                recommendations_count=len(result.coordination_pairs),
                performance_metrics=result.performance_metrics,
                coordination_pairs=result.coordination_pairs,
                settings_analysis=result.settings_analysis,
                protection_zones=result.protection_zones,
                time_current_curves=result.time_current_curves,
                created_by="external_ml_module"
            )
            
            # Save raw result data to file
            result_file = await self._save_result_to_file(ml_result, result.dict())
            ml_result.result_data_path = str(result_file)
            
            # Update job status
            job.status = MLJobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            self.db.add(ml_result)
            self.db.commit()
            self.db.refresh(ml_result)
            
            # Generate recommendations if confidence is high
            if result.confidence_score >= 0.8:
                await self._auto_generate_recommendations(ml_result, result)
            
            return MLResultResponse(
                result_uuid=ml_result.result_uuid,
                job_uuid=job.uuid,
                status="completed",
                result_type="coordination",
                confidence_score=result.confidence_score,
                created_at=ml_result.created_at,
                processing_time_seconds=result.processing_time_seconds,
                recommendations_count=len(result.coordination_pairs)
            )
            
        except Exception as e:
            await self._handle_result_error(job_uuid, str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error submitting coordination result: {str(e)}"
            )
    
    async def submit_selectivity_result(
        self, 
        job_uuid: uuid.UUID, 
        result: MLSelectivityResultRequest
    ) -> MLResultResponse:
        """
        Submit selectivity analysis results from ML module
        """
        try:
            # Validate job
            job = await self._validate_job_for_results(job_uuid, MLAnalysisType.SELECTIVITY)
            
            # Validate result data
            await self._validate_selectivity_result(result)
            
            # Create result record
            ml_result = MLSelectivityResult(
                job_uuid=job.uuid,
                result_uuid=uuid.uuid4(),
                analysis_type=MLAnalysisType.SELECTIVITY,
                status="completed",
                confidence_score=result.confidence_score,
                analysis_summary=result.analysis_summary,
                performance_metrics=result.performance_metrics,
                selectivity_analysis=result.selectivity_analysis,
                fault_scenarios=result.fault_scenarios,
                protection_settings=result.protection_settings,
                time_grading_results=result.time_grading_results,
                created_by="external_ml_module"
            )
            
            # Save result data
            result_file = await self._save_result_to_file(ml_result, result.dict())
            ml_result.result_data_path = str(result_file)
            
            # Update job
            job.status = MLJobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            self.db.add(ml_result)
            self.db.commit()
            self.db.refresh(ml_result)
            
            return MLResultResponse(
                result_uuid=ml_result.result_uuid,
                job_uuid=job.uuid,
                status="completed",
                result_type="selectivity",
                confidence_score=result.confidence_score,
                created_at=ml_result.created_at,
                processing_time_seconds=result.processing_time_seconds,
                recommendations_count=0  # Will be set if recommendations are generated
            )
            
        except Exception as e:
            await self._handle_result_error(job_uuid, str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error submitting selectivity result: {str(e)}"
            )
    
    async def submit_simulation_result(
        self, 
        job_uuid: uuid.UUID, 
        result: MLSimulationResultRequest
    ) -> MLResultResponse:
        """
        Submit simulation analysis results from ML module
        """
        try:
            # Validate job
            job = await self._validate_job_for_results(job_uuid, MLAnalysisType.SIMULATION)
            
            # Validate result data
            await self._validate_simulation_result(result)
            
            # Create result record
            ml_result = MLSimulationResult(
                job_uuid=job.uuid,
                result_uuid=uuid.uuid4(),
                analysis_type=MLAnalysisType.SIMULATION,
                status="completed",
                confidence_score=result.confidence_score,
                analysis_summary=result.analysis_summary,
                performance_metrics=result.performance_metrics,
                simulation_results=result.simulation_results,
                scenario_analysis=result.scenario_analysis,
                optimization_suggestions=result.optimization_suggestions,
                performance_comparison=result.performance_comparison,
                created_by="external_ml_module"
            )
            
            # Save result data
            result_file = await self._save_result_to_file(ml_result, result.dict())
            ml_result.result_data_path = str(result_file)
            
            # Update job
            job.status = MLJobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            self.db.add(ml_result)
            self.db.commit()
            self.db.refresh(ml_result)
            
            return MLResultResponse(
                result_uuid=ml_result.result_uuid,
                job_uuid=job.uuid,
                status="completed",
                result_type="simulation",
                confidence_score=result.confidence_score,
                created_at=ml_result.created_at,
                processing_time_seconds=result.processing_time_seconds,
                recommendations_count=len(result.optimization_suggestions)
            )
            
        except Exception as e:
            await self._handle_result_error(job_uuid, str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Error submitting simulation result: {str(e)}"
            )
    
    async def submit_recommendation(
        self, 
        result_uuid: uuid.UUID, 
        recommendation: MLRecommendationRequest
    ) -> MLRecommendationResponse:
        """
        Submit ML-generated recommendations
        """
        try:
            # Validate recommendation data
            await self._validate_recommendation_request(recommendation)
            
            # Create recommendation record
            ml_recommendation = MLRecommendation(
                result_uuid=result_uuid,
                recommendation_uuid=uuid.uuid4(),
                recommendation_type=MLRecommendationType(recommendation.recommendation_type),
                title=recommendation.title,
                description=recommendation.description,
                priority=recommendation.priority,
                confidence_score=recommendation.confidence_score,
                impact_assessment=recommendation.impact_assessment,
                implementation_steps=recommendation.implementation_steps,
                affected_equipment=recommendation.affected_equipment,
                parameter_changes=recommendation.parameter_changes,
                validation_results=recommendation.validation_results,
                estimated_improvement=recommendation.estimated_improvement,
                risk_assessment=recommendation.risk_assessment,
                created_by="external_ml_module"
            )
            
            # Save to database
            self.db.add(ml_recommendation)
            self.db.commit()
            self.db.refresh(ml_recommendation)
            
            return MLRecommendationResponse(
                recommendation_uuid=ml_recommendation.recommendation_uuid,
                result_uuid=result_uuid,
                recommendation_type=recommendation.recommendation_type,
                title=recommendation.title,
                priority=recommendation.priority,
                confidence_score=recommendation.confidence_score,
                status="submitted",
                created_at=ml_recommendation.created_at,
                affected_equipment_count=len(recommendation.affected_equipment),
                parameter_changes_count=len(recommendation.parameter_changes)
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error submitting recommendation: {str(e)}"
            )
    
    async def get_job_results(self, job_uuid: uuid.UUID) -> List[MLResultResponse]:
        """
        Get all results for a specific job
        """
        try:
            # Get job
            job = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.uuid == job_uuid
            ).first()
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            results = []
            
            # Get coordination results
            coord_results = self.db.query(MLCoordinationResult).filter(
                MLCoordinationResult.job_uuid == job_uuid
            ).all()
            
            for result in coord_results:
                results.append(MLResultResponse(
                    result_uuid=result.result_uuid,
                    job_uuid=job_uuid,
                    status=result.status,
                    result_type="coordination",
                    confidence_score=result.confidence_score,
                    created_at=result.created_at,
                    processing_time_seconds=None,  # Can be extracted from performance_metrics
                    recommendations_count=result.recommendations_count
                ))
            
            # Get selectivity results
            sel_results = self.db.query(MLSelectivityResult).filter(
                MLSelectivityResult.job_uuid == job_uuid
            ).all()
            
            for result in sel_results:
                results.append(MLResultResponse(
                    result_uuid=result.result_uuid,
                    job_uuid=job_uuid,
                    status=result.status,
                    result_type="selectivity",
                    confidence_score=result.confidence_score,
                    created_at=result.created_at,
                    processing_time_seconds=None,
                    recommendations_count=0
                ))
            
            # Get simulation results
            sim_results = self.db.query(MLSimulationResult).filter(
                MLSimulationResult.job_uuid == job_uuid
            ).all()
            
            for result in sim_results:
                results.append(MLResultResponse(
                    result_uuid=result.result_uuid,
                    job_uuid=job_uuid,
                    status=result.status,
                    result_type="simulation",
                    confidence_score=result.confidence_score,
                    created_at=result.created_at,
                    processing_time_seconds=None,
                    recommendations_count=0
                ))
            
            return results
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting job results: {str(e)}"
            )
    
    async def get_recommendations(
        self, 
        result_uuid: Optional[uuid.UUID] = None,
        recommendation_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[MLRecommendationResponse]:
        """
        Get recommendations with optional filtering
        """
        try:
            query = self.db.query(MLRecommendation)
            
            if result_uuid:
                query = query.filter(MLRecommendation.result_uuid == result_uuid)
            
            if recommendation_type:
                query = query.filter(MLRecommendation.recommendation_type == recommendation_type)
            
            if min_confidence:
                query = query.filter(MLRecommendation.confidence_score >= min_confidence)
            
            recommendations = query.order_by(desc(MLRecommendation.created_at)).all()
            
            response_list = []
            for rec in recommendations:
                response_list.append(MLRecommendationResponse(
                    recommendation_uuid=rec.recommendation_uuid,
                    result_uuid=rec.result_uuid,
                    recommendation_type=rec.recommendation_type.value,
                    title=rec.title,
                    priority=rec.priority,
                    confidence_score=rec.confidence_score,
                    status="active",  # Could be enhanced with status tracking
                    created_at=rec.created_at,
                    affected_equipment_count=len(rec.affected_equipment) if rec.affected_equipment else 0,
                    parameter_changes_count=len(rec.parameter_changes) if rec.parameter_changes else 0
                ))
            
            return response_list
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting recommendations: {str(e)}"
            )
    
    async def update_job_status(self, job_uuid: uuid.UUID, status: str, message: Optional[str] = None) -> MLJobStatusResponse:
        """
        Update job status from ML module
        """
        try:
            job = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.uuid == job_uuid
            ).first()
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Validate status transition
            if not self._is_valid_status_transition(job.status, MLJobStatus(status)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status transition from {job.status.value} to {status}"
                )
            
            # Update job
            job.status = MLJobStatus(status)
            job.updated_at = datetime.now(timezone.utc)
            
            if message:
                if not job.processing_logs:
                    job.processing_logs = []
                job.processing_logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": message,
                    "status": status
                })
            
            self.db.commit()
            self.db.refresh(job)
            
            return MLJobStatusResponse(
                job_uuid=job.uuid,
                status=job.status.value,
                message=message,
                updated_at=job.updated_at,
                progress_percentage=self._calculate_progress(job.status),
                estimated_completion=self._estimate_completion(job)
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error updating job status: {str(e)}"
            )
    
    # ===== PRIVATE METHODS =====
    
    async def _validate_job_for_results(self, job_uuid: uuid.UUID, expected_type: MLAnalysisType) -> MLAnalysisJob:
        """Validate job exists and is ready for results"""
        job = self.db.query(MLAnalysisJob).filter(
            MLAnalysisJob.uuid == job_uuid
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.analysis_type != expected_type:
            raise HTTPException(
                status_code=400, 
                detail=f"Job type mismatch: expected {expected_type.value}, got {job.analysis_type.value}"
            )
        
        if job.status not in [MLJobStatus.RUNNING, MLJobStatus.PROCESSING]:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not in a state to receive results: {job.status.value}"
            )
        
        return job
    
    async def _validate_coordination_result(self, result: MLCoordinationResultRequest):
        """Validate coordination result data"""
        if result.confidence_score < 0 or result.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if not result.coordination_pairs:
            raise ValueError("Coordination pairs cannot be empty")
        
        # Additional validation logic here
    
    async def _validate_selectivity_result(self, result: MLSelectivityResultRequest):
        """Validate selectivity result data"""
        if result.confidence_score < 0 or result.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if not result.selectivity_analysis:
            raise ValueError("Selectivity analysis cannot be empty")
    
    async def _validate_simulation_result(self, result: MLSimulationResultRequest):
        """Validate simulation result data"""
        if result.confidence_score < 0 or result.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if not result.simulation_results:
            raise ValueError("Simulation results cannot be empty")
    
    async def _validate_recommendation_request(self, recommendation: MLRecommendationRequest):
        """Validate recommendation request"""
        if recommendation.confidence_score < 0 or recommendation.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        
        if recommendation.priority not in ["low", "medium", "high", "critical"]:
            raise ValueError("Invalid priority level")
    
    async def _save_result_to_file(self, ml_result, result_data: dict) -> Path:
        """Save result data to file"""
        file_name = f"{ml_result.result_uuid.hex[:8]}_{ml_result.analysis_type.value}_result.json"
        file_path = self.results_path / file_name
        
        with open(file_path, 'w') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        return file_path
    
    async def _handle_result_error(self, job_uuid: uuid.UUID, error_message: str):
        """Handle result submission errors"""
        try:
            job = self.db.query(MLAnalysisJob).filter(
                MLAnalysisJob.uuid == job_uuid
            ).first()
            
            if job:
                job.status = MLJobStatus.FAILED
                job.updated_at = datetime.now(timezone.utc)
                
                if not job.processing_logs:
                    job.processing_logs = []
                job.processing_logs.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": error_message,
                    "status": "failed"
                })
                
                self.db.commit()
        except Exception:
            pass  # Don't fail on error handling
    
    async def _auto_generate_recommendations(self, ml_result, result_data):
        """Auto-generate recommendations for high-confidence results"""
        # Implementation for automatic recommendation generation
        # based on high-confidence ML results
        pass
    
    def _is_valid_status_transition(self, current: MLJobStatus, new: MLJobStatus) -> bool:
        """Validate job status transitions"""
        valid_transitions = {
            MLJobStatus.PENDING: [MLJobStatus.RUNNING, MLJobStatus.FAILED, MLJobStatus.CANCELLED],
            MLJobStatus.RUNNING: [MLJobStatus.PROCESSING, MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED],
            MLJobStatus.PROCESSING: [MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED],
            MLJobStatus.COMPLETED: [],  # Terminal state
            MLJobStatus.FAILED: [],     # Terminal state
            MLJobStatus.CANCELLED: []   # Terminal state
        }
        
        return new in valid_transitions.get(current, [])
    
    def _calculate_progress(self, status: MLJobStatus) -> float:
        """Calculate progress percentage based on status"""
        progress_map = {
            MLJobStatus.PENDING: 0.0,
            MLJobStatus.RUNNING: 25.0,
            MLJobStatus.PROCESSING: 75.0,
            MLJobStatus.COMPLETED: 100.0,
            MLJobStatus.FAILED: 0.0,
            MLJobStatus.CANCELLED: 0.0
        }
        return progress_map.get(status, 0.0)
    
    def _estimate_completion(self, job: MLAnalysisJob) -> Optional[datetime]:
        """Estimate job completion time"""
        # Simple estimation logic - in production would be more sophisticated
        if job.status in [MLJobStatus.COMPLETED, MLJobStatus.FAILED, MLJobStatus.CANCELLED]:
            return None
        
        # Estimate based on analysis type and current progress
        estimation_hours = {
            MLAnalysisType.COORDINATION: 2,
            MLAnalysisType.SELECTIVITY: 3,
            MLAnalysisType.SIMULATION: 4
        }
        
        hours = estimation_hours.get(job.analysis_type, 2)
        return datetime.now(timezone.utc).replace(hour=datetime.now().hour + hours)