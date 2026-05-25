from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.job import ScrapingJobCreate, ScrapingJobInDB, ScrapingJobUpdate
from api.services.job_service import JobService

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", response_model=ScrapingJobInDB, status_code=201)
async def create_job(job_data: ScrapingJobCreate):
    """Create a new scraping job."""
    return await JobService.create_job(job_data)


@router.get("", response_model=list[ScrapingJobInDB])
async def list_jobs(
    status: Optional[str] = Query(None, pattern="^(active|paused|error)$"),
    tags: Optional[list[str]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List all scraping jobs with optional filtering."""
    return await JobService.list_jobs(status=status, tags=tags, skip=skip, limit=limit)


@router.get("/{job_id}", response_model=ScrapingJobInDB)
async def get_job(job_id: str):
    """Get a job by ID."""
    job = await JobService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}", response_model=ScrapingJobInDB)
async def update_job(job_id: str, job_data: ScrapingJobUpdate):
    """Update an existing job."""
    job = await JobService.update_job(job_id, job_data)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Delete a job."""
    deleted = await JobService.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/{job_id}/pause", response_model=ScrapingJobInDB)
async def pause_job(job_id: str):
    """Pause a job."""
    job = await JobService.pause_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/resume", response_model=ScrapingJobInDB)
async def resume_job(job_id: str):
    """Resume a paused job."""
    job = await JobService.resume_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
