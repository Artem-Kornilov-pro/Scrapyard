from datetime import UTC, datetime, timedelta
from typing import Any

from api.core.database import db


class AnalyticsService:
    """Service for analytics using MongoDB aggregations."""

    @staticmethod
    async def get_job_stats(job_id: str, days: int = 30) -> list[dict[str, Any]]:
        """Get daily statistics for a job."""
        assert db.scraped_results is not None

        since = datetime.now(UTC) - timedelta(days=days)
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "job_id": job_id,
                    "timestamp": {"$gte": since},
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$timestamp",
                        }
                    },
                    "runs": {"$sum": 1},
                    "total_items": {"$sum": "$items_count"},
                    "avg_duration": {"$avg": "$metadata.duration_ms"},
                    "errors": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$metadata.status", "failed"]},
                                1,
                                0,
                            ]
                        }
                    },
                }
            },
            {"$sort": {"_id": 1}},
        ]

        cursor = db.scraped_results.aggregate(pipeline)
        return await cursor.to_list(length=None)

    @staticmethod
    async def get_slowest_jobs(limit: int = 5) -> list[dict[str, Any]]:
        """Get top N slowest active jobs by average duration."""
        assert db.scraped_results is not None

        pipeline: list[dict[str, Any]] = [
            {"$match": {"metadata.status": "success"}},
            {
                "$group": {
                    "_id": "$job_id",
                    "avg_duration": {"$avg": "$metadata.duration_ms"},
                    "last_run": {"$max": "$timestamp"},
                }
            },
            {
                "$lookup": {
                    "from": "scraping_jobs",
                    "localField": "_id",
                    "foreignField": "job_id",
                    "as": "job_config",
                }
            },
            {"$unwind": "$job_config"},
            {"$match": {"job_config.status": "active"}},
            {"$sort": {"avg_duration": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "job_id": "$_id",
                    "name": "$job_config.name",
                    "avg_duration": 1,
                    "last_run": 1,
                    "_id": 0,
                }
            },
        ]

        cursor = db.scraped_results.aggregate(pipeline)
        return await cursor.to_list(length=None)

    @staticmethod
    async def get_success_rate(days: int = 7) -> dict[str, Any]:
        """Get overall success rate for the last N days."""
        assert db.scraped_results is not None

        since = datetime.now(UTC) - timedelta(days=days)
        pipeline: list[dict[str, Any]] = [
            {"$match": {"timestamp": {"$gte": since}}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "successes": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$metadata.status", "success"]},
                                1,
                                0,
                            ]
                        }
                    },
                    "failures": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$metadata.status", "failed"]},
                                1,
                                0,
                            ]
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "total": 1,
                    "successes": 1,
                    "failures": 1,
                    "success_rate": {
                        "$cond": [
                            {"$gt": ["$total", 0]},
                            {
                                "$round": [
                                    {
                                        "$multiply": [
                                            {"$divide": ["$successes", "$total"]},
                                            100,
                                        ]
                                    },
                                    2,
                                ]
                            },
                            0,
                        ]
                    },
                }
            },
        ]

        cursor = db.scraped_results.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if results:
            return results[0]
        else:
            return {"total": 0, "successes": 0, "failures": 0, "success_rate": 0}


    @staticmethod
    async def get_overview() -> dict[str, Any]:
        """Get overall system overview."""
        assert db.scraping_jobs is not None
        assert db.scraped_results is not None

        total_jobs = await db.scraping_jobs.count_documents({})
        active_jobs = await db.scraping_jobs.count_documents({"status": "active"})
        paused_jobs = await db.scraping_jobs.count_documents({"status": "paused"})
        error_jobs = await db.scraping_jobs.count_documents({"status": "error"})
        total_results = await db.scraped_results.count_documents({})

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "paused_jobs": paused_jobs,
            "error_jobs": error_jobs,
            "total_results": total_results,
        }
