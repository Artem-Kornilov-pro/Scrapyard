from fastapi import APIRouter, Depends, Query

from api.core.rate_limit import enforce_rate_limit
from api.core.security import verify_api_key
from api.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
    dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)],
)


@router.get("/jobs/{job_id}/stats")
async def get_job_stats(job_id: str, days: int = Query(30, ge=1, le=365)):
    """Get daily statistics for a specific job."""
    return await AnalyticsService.get_job_stats(job_id, days)


@router.get("/slowest")
async def get_slowest_jobs(limit: int = Query(5, ge=1, le=20)):
    """Get top N slowest active jobs."""
    return await AnalyticsService.get_slowest_jobs(limit)


@router.get("/success-rate")
async def get_success_rate(days: int = Query(7, ge=1, le=90)):
    """Get overall success rate."""
    return await AnalyticsService.get_success_rate(days)


@router.get("/overview")
async def get_overview():
    """Get system overview."""
    return await AnalyticsService.get_overview()
