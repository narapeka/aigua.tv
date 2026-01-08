"""
Jobs API Routes
Endpoints for dry-run and execution operations
"""

import uuid
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Optional

from app.models.api_models import (
    DryRunRequest,
    DryRunResponse,
    JobResult,
    JobStatus,
    SelectionUpdateRequest,
    CategoryUpdateRequest,
    ReassignTMDBRequest,
    ExecuteRequest,
    ErrorResponse
)
from app.services.cache_service import get_cache_service, CacheService
from app.services.job_service import JobService
from app.core.organizer_wrapper import OrganizerWrapper

router = APIRouter()


def get_job_service() -> JobService:
    """Dependency to get job service"""
    cache = get_cache_service()
    return JobService(cache)


async def run_dry_run_task(
    job_id: str,
    input_dir: str,
    output_dir: str,
    job_service: JobService
):
    """Background task to run dry-run"""
    try:
        # Update status to running
        job_service.update_job_status(job_id, JobStatus.RUNNING)

        # Run dry-run
        result = OrganizerWrapper.run_dry_run(
            input_dir=input_dir,
            output_dir=output_dir
        )

        # Update job with results
        job_service.update_job_result(
            job_id=job_id,
            stats=result["stats"],
            processed_shows=result["processed_shows"],
            unprocessed_shows=result["unprocessed_shows"],
            status=JobStatus.COMPLETED
        )

    except Exception as e:
        # Update status to failed
        job_service.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e)
        )
        print(f"✗ Dry-run failed for job {job_id}: {e}")


@router.post("/jobs/dry-run", response_model=DryRunResponse)
async def start_dry_run(
    request: DryRunRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service)
):
    """
    Start a dry-run operation

    This scans the input directory, extracts show names using LLM,
    fetches TMDB metadata, and returns the organization plan without
    moving any files.
    """
    job_id = str(uuid.uuid4())

    # Create job
    job_service.create_job(
        job_id=job_id,
        input_dir=request.input_dir,
        output_dir=request.output_dir,
        status=JobStatus.PENDING
    )

    # Run dry-run in background
    background_tasks.add_task(
        run_dry_run_task,
        job_id,
        request.input_dir,
        request.output_dir,
        job_service
    )

    return DryRunResponse(
        job_id=job_id,
        status=JobStatus.RUNNING
    )


@router.get("/jobs/{job_id}", response_model=JobResult)
async def get_job_result(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """
    Get job result

    Returns the current state of the job including all shows,
    seasons, episodes, and selection states.
    """
    job_data = job_service.get_job(job_id)

    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or expired"
        )

    return JobResult(**job_data)


@router.post("/jobs/{job_id}/execute")
async def execute_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service)
):
    """
    Execute organization for selected shows

    Uses the cached dry-run results and only organizes shows/seasons/episodes
    that are marked as selected.
    """
    job_data = job_service.get_job(job_id)

    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or expired"
        )

    if job_data["status"] != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed before execution. Current status: {job_data['status']}"
        )

    # Update status to running
    job_service.update_job_status(job_id, JobStatus.RUNNING)

    # Execute in background
    async def execute_task():
        try:
            result = OrganizerWrapper.execute_selected(
                input_dir=job_data["input_dir"],
                output_dir=job_data["output_dir"],
                processed_shows=job_data["processed_shows"]
            )

            # Update stats
            job_data["stats"] = result["stats"]
            job_data["status"] = JobStatus.COMPLETED.value

            job_service.cache.update_job(job_id, job_data)

        except Exception as e:
            job_service.update_job_status(
                job_id,
                JobStatus.FAILED,
                error=str(e)
            )
            print(f"✗ Execution failed for job {job_id}: {e}")

    background_tasks.add_task(execute_task)

    return {"status": "executing", "job_id": job_id}


@router.put("/jobs/{job_id}/shows/{show_id}/select")
async def update_show_selection(
    job_id: str,
    show_id: str,
    request: SelectionUpdateRequest,
    job_service: JobService = Depends(get_job_service)
):
    """Update show selection state"""
    try:
        job_service.update_show_selection(job_id, show_id, request.selected)
        return {"status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/jobs/{job_id}/shows/{show_id}/seasons/{season_number}/select")
async def update_season_selection(
    job_id: str,
    show_id: str,
    season_number: int,
    request: SelectionUpdateRequest,
    job_service: JobService = Depends(get_job_service)
):
    """Update season selection state"""
    try:
        job_service.update_season_selection(job_id, show_id, season_number, request.selected)
        return {"status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/jobs/{job_id}/shows/{show_id}/category")
async def update_show_category(
    job_id: str,
    show_id: str,
    request: CategoryUpdateRequest,
    job_service: JobService = Depends(get_job_service)
):
    """Update show category"""
    try:
        job_service.update_show_category(job_id, show_id, request.category)
        return {"status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """Delete job and cleanup cache"""
    job_service.delete_job(job_id)
    return {"status": "deleted"}
