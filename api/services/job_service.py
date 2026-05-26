from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from croniter import croniter  # type: ignore[import-untyped]

from api.core.cache import analytics_cache, jobs_cache
from api.core.database import db
from api.models.job import ScrapingJobCreate, ScrapingJobInDB, ScrapingJobUpdate


class JobService:
    """Service layer for scraping job operations."""

    @staticmethod
    async def create_job(job_data: ScrapingJobCreate) -> ScrapingJobInDB:
        """Create a new scraping job."""
        now = datetime.now(UTC)
        job = ScrapingJobInDB(
            job_id=str(uuid4()),
            **job_data.model_dump(),
            next_run=JobService._calculate_next_run(job_data.schedule),
            created_at=now,
            updated_at=now,
        )
        assert db.scraping_jobs is not None
        await db.scraping_jobs.insert_one(job.model_dump())
        await jobs_cache.delete_pattern("jobs:*")
        await analytics_cache.delete_pattern("analytics:*")
        return job

    @staticmethod
    async def get_job(job_id: str) -> ScrapingJobInDB | None:
        """Get a job by ID."""
        assert db.scraping_jobs is not None
        doc = await db.scraping_jobs.find_one({"job_id": job_id})
        if doc:
            return ScrapingJobInDB(**doc)
        return None

    @staticmethod
    async def list_jobs(
        status: str | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ScrapingJobInDB]:
        """List jobs with optional filtering and pagination."""
        assert db.scraping_jobs is not None
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if tags:
            query["tags"] = {"$in": tags}

        cursor = db.scraping_jobs.find(query).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [ScrapingJobInDB(**doc) for doc in docs]

    @staticmethod
    async def update_job(
        job_id: str, job_data: ScrapingJobUpdate
    ) -> ScrapingJobInDB | None:
        """Update an existing job."""
        assert db.scraping_jobs is not None
        existing = await db.scraping_jobs.find_one({"job_id": job_id})
        if not existing:
            return None

        update_data = job_data.model_dump(exclude_unset=True)
        if not update_data:
            return ScrapingJobInDB(**existing)

        update_data["updated_at"] = datetime.now(UTC)

        if "schedule" in update_data:
            update_data["next_run"] = JobService._calculate_next_run(
                update_data["schedule"]
            )

        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {"$set": update_data},
        )
        await jobs_cache.delete_pattern("jobs:*")

        updated = await db.scraping_jobs.find_one({"job_id": job_id})
        assert updated is not None
        return ScrapingJobInDB(**updated)

    @staticmethod
    async def delete_job(job_id: str) -> bool:
        """Delete a job by ID."""
        assert db.scraping_jobs is not None
        result = await db.scraping_jobs.delete_one({"job_id": job_id})
        await jobs_cache.delete_pattern("jobs:*")
        return bool(result.deleted_count > 0)

    @staticmethod
    async def pause_job(job_id: str) -> ScrapingJobInDB | None:
        """Pause a job."""
        result = await JobService._change_status(job_id, "paused")
        await jobs_cache.delete_pattern("jobs:*")
        return result

    @staticmethod
    async def resume_job(job_id: str) -> ScrapingJobInDB | None:
        """Resume a paused job."""
        assert db.scraping_jobs is not None
        existing = await db.scraping_jobs.find_one({"job_id": job_id})
        if not existing:
            return None

        update_data = {
            "status": "active",
            "next_run": JobService._calculate_next_run(
                existing["schedule"], datetime.now(UTC)
            ),
            "updated_at": datetime.now(UTC),
        }

        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {"$set": update_data},
        )
        await jobs_cache.delete_pattern("jobs:*")

        updated = await db.scraping_jobs.find_one({"job_id": job_id})
        assert updated is not None
        return ScrapingJobInDB(**updated)

    @staticmethod
    async def _change_status(
        job_id: str, status: str
    ) -> ScrapingJobInDB | None:
        """Change job status."""
        assert db.scraping_jobs is not None
        existing = await db.scraping_jobs.find_one({"job_id": job_id})
        if not existing:
            return None

        await db.scraping_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": status, "updated_at": datetime.now(UTC)}},
        )

        updated = await db.scraping_jobs.find_one({"job_id": job_id})
        assert updated is not None
        return ScrapingJobInDB(**updated)

    @staticmethod
    def _calculate_next_run(
        cron_expr: str, base_time: datetime | None = None
    ) -> datetime:
        """Calculate next run time from cron expression."""
        if base_time is None:
            base_time = datetime.now(UTC)
        cron: croniter = croniter(cron_expr, base_time)
        result: datetime = cron.get_next(datetime)
        return result
