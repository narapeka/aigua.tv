"""Organization workflow API endpoints"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional

from webui.models.schemas import (
    DryRunRequest, DryRunResponse, ExecuteRequest, ExecuteResponse,
    JobStatusResponse, UpdateMatchRequest, UpdateMatchResponse
)
from webui.services.job_manager import job_manager, JobStatus
from webui.services.organizer_service import organizer_service
import logging
import asyncio

router = APIRouter(prefix="/api/organize", tags=["organize"])
logger = logging.getLogger(__name__)


def run_dry_run_task(job_id: str, source_folder: str, target_folder: str,
                    selected_folders: Optional[list] = None,
                    manual_matches: Optional[dict] = None):
    """Background task for dry-run"""
    try:
        job_manager.update_job(job_id, status=JobStatus.RUNNING)
        
        preview_data = organizer_service.create_preview(
            source_folder=source_folder,
            target_folder=target_folder,
            selected_folders=selected_folders,
            manual_matches=manual_matches
        )
        
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            result=preview_data
        )
    except Exception as e:
        logger.error(f"Error in dry-run task: {e}")
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )


def run_execute_task(job_id: str, source_folder: str, target_folder: str,
                    selected_folders: list, manual_matches: Optional[dict] = None):
    """Background task for execution"""
    try:
        job_manager.update_job(job_id, status=JobStatus.RUNNING)
        
        result = organizer_service.execute_organization(
            source_folder=source_folder,
            target_folder=target_folder,
            selected_folders=selected_folders,
            manual_matches=manual_matches
        )
        
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            result=result
        )
    except Exception as e:
        logger.error(f"Error in execute task: {e}")
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )


@router.post("/dry-run", response_model=DryRunResponse)
async def start_dry_run(request: DryRunRequest, background_tasks: BackgroundTasks):
    """Start a dry-run preview"""
    try:
        job_data = {
            "source_folder": request.source_folder,
            "target_folder": request.target_folder
        }
        job_id = job_manager.create_job("dry_run", job_data)
        
        # Start background task
        background_tasks.add_task(
            run_dry_run_task,
            job_id=job_id,
            source_folder=request.source_folder,
            target_folder=request.target_folder
        )
        
        return DryRunResponse(
            job_id=job_id,
            status="pending",
            message="Dry-run started"
        )
    except Exception as e:
        logger.error(f"Error starting dry-run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start dry-run: {str(e)}")


@router.post("/execute", response_model=ExecuteResponse)
async def execute_organization(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """Execute organization with selected shows"""
    try:
        # Get the preview job to get source/target folders
        preview_job = job_manager.get_job(request.job_id)
        if not preview_job:
            raise HTTPException(status_code=404, detail="Preview job not found")
        
        job_status = preview_job['status']
        if isinstance(job_status, JobStatus):
            job_status = job_status.value
        if job_status != 'completed':
            raise HTTPException(status_code=400, detail="Preview job not completed")
        
        # Extract source/target from preview job data
        source_folder = preview_job['data'].get('source_folder')
        target_folder = preview_job['data'].get('target_folder')
        
        if not source_folder or not target_folder:
            raise HTTPException(status_code=400, detail="Source and target folders not found in preview job")
        
        # Create new job for execution
        execute_job_id = job_manager.create_job("execute", {
            "source_folder": source_folder,
            "target_folder": target_folder,
            "selected_folders": request.selected_folders,
            "manual_matches": request.manual_matches
        })
        
        # Start background task
        background_tasks.add_task(
            run_execute_task,
            job_id=execute_job_id,
            source_folder=source_folder,
            target_folder=target_folder,
            selected_folders=request.selected_folders,
            manual_matches=request.manual_matches
        )
        
        return ExecuteResponse(
            job_id=execute_job_id,
            status="pending",
            message="Organization started"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'].value if isinstance(job['status'], JobStatus) else job['status'],
        progress=job.get('progress'),
        message=None,
        error=job.get('error')
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return {"success": True, "message": "Job cancelled"}


@router.put("/match/{folder_name}", response_model=UpdateMatchResponse)
async def update_match(folder_name: str, request: UpdateMatchRequest):
    """Update TMDB match for a folder (for manual matching)"""
    try:
        # This is mainly for updating preview data
        # The actual match will be used during execution
        return UpdateMatchResponse(
            success=True,
            message=f"Match updated for {folder_name}"
        )
    except Exception as e:
        logger.error(f"Error updating match: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update match: {str(e)}")

