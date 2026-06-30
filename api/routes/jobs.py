from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.core.cache import jobs_cache
from api.core.rate_limit import enforce_rate_limit
from api.core.security import verify_api_key
from api.models.job import (
    DryRunRequest,
    DryRunResult,
    ScrapingJobCreate,
    ScrapingJobInDB,
    ScrapingJobUpdate,
)
from api.services.job_service import JobService

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["jobs"],
    dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)],
)


@router.post("", response_model=ScrapingJobInDB, status_code=201)
async def create_job(job_data: ScrapingJobCreate):
    """Create a new scraping job."""
    return await JobService.create_job(job_data)


@router.post("/dry-run", response_model=DryRunResult)
async def dry_run_job(payload: DryRunRequest):
    """Test selectors against a live page without creating a job."""
    result = await JobService.dry_run(payload)
    if result is None:
        raise HTTPException(
            status_code=504, detail="Dry run timed out waiting for a worker"
        )
    return result


@router.get("", response_model=list[ScrapingJobInDB])
async def list_jobs(
    status: Optional[str] = Query(None, pattern="^(active|paused|error)$"),
    tags: Optional[list[str]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List all scraping jobs with optional filtering."""
    cache_key = f"jobs:list:{status}:{','.join(tags or [])}:{skip}:{limit}"
    cached = await jobs_cache.get(cache_key)
    if cached is not None:
        return cached

    result = await JobService.list_jobs(
        status=status, tags=tags, skip=skip, limit=limit
    )
    await jobs_cache.set(cache_key, result)
    return result


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


@router.post("/{job_id}/run", status_code=202)
async def run_job_now(job_id: str):
    """Dispatch a job to the worker immediately, bypassing its schedule."""
    result = await JobService.run_now(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result
