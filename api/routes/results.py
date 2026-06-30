import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.core.database import db
from api.core.rate_limit import enforce_rate_limit
from api.core.security import verify_api_key
from api.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["results"],
    dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)],
)


@router.get("/{job_id}/results")
async def list_job_results(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List scrape results for a job, most recent first."""
    assert db.scraped_results is not None
    cursor = (
        db.scraped_results.find({"job_id": job_id}, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


@router.get("/{job_id}/results/diff")
async def diff_job_results(
    job_id: str,
    run_a: str | None = Query(None, description="Older run_id to compare"),
    run_b: str | None = Query(None, description="Newer run_id to compare"),
):
    """Diff two runs of a job. Defaults to the two most recent runs."""
    diff = await AnalyticsService.get_diff(job_id, run_a, run_b)
    if diff is None:
        raise HTTPException(
            status_code=404,
            detail="Not enough runs to diff (need at least 2), or a "
            "given run_id wasn't found",
        )
    return diff


@router.get("/{job_id}/results/export")
async def export_job_results(
    job_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    run_id: str | None = Query(
        None, description="Export a specific run; defaults to the latest"
    ),
):
    """Export a run's scraped items as JSON or CSV."""
    assert db.scraped_results is not None

    if run_id:
        result = await db.scraped_results.find_one(
            {"job_id": job_id, "run_id": run_id}, {"_id": 0}
        )
    else:
        result = await db.scraped_results.find_one(
            {"job_id": job_id}, projection={"_id": 0}, sort=[("timestamp", -1)]
        )

    if result is None:
        raise HTTPException(status_code=404, detail="No results found for this job")

    items: list[dict[str, Any]] = result.get("items", [])

    if format == "csv":
        filename = f"{job_id}_{result['run_id']}.csv"
        return Response(
            content=_items_to_csv(items),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return JSONResponse(content=jsonable_encoder(items))


def _items_to_csv(items: list[dict[str, Any]]) -> str:
    """Flatten scraped items into CSV. Field order follows first
    appearance across items; later items may introduce new columns.
    """
    if not items:
        return ""

    fieldnames: list[str] = []
    for item in items:
        for key in item:
            if key not in fieldnames:
                fieldnames.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(items)
    return buffer.getvalue()
