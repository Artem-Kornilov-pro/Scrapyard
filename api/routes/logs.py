from fastapi import APIRouter, Query

from api.core.database import db

router = APIRouter(prefix="/api/v1", tags=["logs"])


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Get logs for a specific job."""
    assert db.job_logs is not None

    cursor = db.job_logs.find(
        {"job_id": job_id}).sort("timestamp", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


@router.get("/logs")
async def get_all_logs(
    status: str = Query(None, pattern="^(started|completed|failed)$"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Get all logs with optional status filter."""
    assert db.job_logs is not None

    query = {}
    if status:
        query["status"] = status

    cursor = db.job_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)
