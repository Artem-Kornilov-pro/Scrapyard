from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from api.core.cache import analytics_cache
from api.core.database import db


class AnalyticsService:
    """Service for analytics using MongoDB aggregations."""

    @staticmethod
    async def get_job_stats(job_id: str, days: int = 30) -> list[dict[str, Any]]:
        """Get daily statistics for a job."""
        cache_key = f"analytics:job_stats:{job_id}:{days}"
        cached: list[dict[str, Any]] | None = await analytics_cache.get(cache_key)
        if cached is not None:
            return cached

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
        result = await cursor.to_list(length=None)
        await analytics_cache.set(cache_key, result)
        return cast(list[dict[str, Any]], result)

    @staticmethod
    async def get_slowest_jobs(limit: int = 5) -> list[dict[str, Any]]:
        """Get top N slowest active jobs."""
        cache_key = f"analytics:slowest:{limit}"
        cached: list[dict[str, Any]] | None = await analytics_cache.get(cache_key)
        if cached is not None:
            return cached

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
        result = await cursor.to_list(length=None)
        await analytics_cache.set(cache_key, result)
        return cast(list[dict[str, Any]], result)

    @staticmethod
    async def get_success_rate(days: int = 7) -> dict[str, Any]:
        """Get overall success rate."""
        cache_key = f"analytics:success_rate:{days}"
        cached: dict[str, Any] | None = await analytics_cache.get(cache_key)
        if cached is not None:
            return cached

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
        result = results[0] if results else {
            "total": 0, "successes": 0, "failures": 0, "success_rate": 0,
        }
        await analytics_cache.set(cache_key, result)
        return cast(dict[str, Any], result)

    @staticmethod
    async def get_overview() -> dict[str, Any]:
        """Get overall system overview."""
        cache_key = "analytics:overview"
        cached: dict[str, Any] | None = await analytics_cache.get(cache_key)
        if cached is not None:
            return cached

        if db.scraping_jobs is None or db.scraped_results is None:
            return {
                "total_jobs": 0, "active_jobs": 0,
                "paused_jobs": 0, "error_jobs": 0, "total_results": 0,
            }

        total_jobs = await db.scraping_jobs.count_documents({})
        active_jobs = await db.scraping_jobs.count_documents({"status": "active"})
        paused_jobs = await db.scraping_jobs.count_documents({"status": "paused"})
        error_jobs = await db.scraping_jobs.count_documents({"status": "error"})
        total_results = await db.scraped_results.count_documents({})

        result: dict[str, Any] = {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "paused_jobs": paused_jobs,
            "error_jobs": error_jobs,
            "total_results": total_results,
        }
        await analytics_cache.set(cache_key, result)
        return result

    @staticmethod
    async def invalidate_analytics_cache() -> None:
        """Invalidate all analytics cache."""
        await analytics_cache.delete_pattern("analytics:*")

    @staticmethod
    async def get_diff(
        job_id: str,
        run_a: str | None = None,
        run_b: str | None = None,
    ) -> dict[str, Any] | None:
        """Diff two scrape runs for a job, defaulting to the two most
        recent. Returns None if there aren't two runs to compare, or a
        given run_id doesn't exist.

        If the job has a `diff_key` configured, items are matched across
        runs by that field and diffed per-field (added/removed/changed).
        Without one, items are compared whole, so any field change shows
        up as a remove+add rather than a per-field change.
        """
        assert db.scraped_results is not None
        assert db.scraping_jobs is not None

        if run_a or run_b:
            if not (run_a and run_b):
                return None
            older = await db.scraped_results.find_one(
                {"job_id": job_id, "run_id": run_a}, {"_id": 0}
            )
            newer = await db.scraped_results.find_one(
                {"job_id": job_id, "run_id": run_b}, {"_id": 0}
            )
            if not older or not newer:
                return None
        else:
            cursor = db.scraped_results.find(
                {"job_id": job_id}, {"_id": 0}
            ).sort("timestamp", -1).limit(2)
            docs = await cursor.to_list(length=2)
            if len(docs) < 2:
                return None
            newer, older = docs[0], docs[1]

        job_doc = await db.scraping_jobs.find_one(
            {"job_id": job_id}, {"_id": 0}
        )
        diff_key = (job_doc or {}).get("diff_key")

        older_items = older.get("items", [])
        newer_items = newer.get("items", [])

        if diff_key:
            changes = _diff_items_by_key(older_items, newer_items, diff_key)
        else:
            changes = _diff_items_by_content(older_items, newer_items)

        return {
            "job_id": job_id,
            "diff_key": diff_key,
            "run_a": {
                "run_id": older["run_id"],
                "timestamp": older["timestamp"],
            },
            "run_b": {
                "run_id": newer["run_id"],
                "timestamp": newer["timestamp"],
            },
            **changes,
        }


def _diff_items_by_key(
    older_items: list[dict[str, Any]],
    newer_items: list[dict[str, Any]],
    diff_key: str,
) -> dict[str, Any]:
    """Match items across runs by `diff_key` and diff matched pairs
    field-by-field. Items missing the key are ignored.
    """
    older_map = {
        item[diff_key]: item for item in older_items if diff_key in item
    }
    newer_map = {
        item[diff_key]: item for item in newer_items if diff_key in item
    }

    added = [v for k, v in newer_map.items() if k not in older_map]
    removed = [v for k, v in older_map.items() if k not in newer_map]

    changed = []
    for key in older_map.keys() & newer_map.keys():
        old_item, new_item = older_map[key], newer_map[key]
        field_changes = {
            field: {"old": old_item.get(field), "new": new_item.get(field)}
            for field in set(old_item) | set(new_item)
            if old_item.get(field) != new_item.get(field)
        }
        if field_changes:
            changed.append({"key": key, "changes": field_changes})

    return {"added": added, "removed": removed, "changed": changed}


def _diff_items_by_content(
    older_items: list[dict[str, Any]],
    newer_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare items by full equality — no identity field is configured
    to match them across runs, so a changed field looks like a
    remove+add rather than a per-field change.
    """
    def _fingerprint(item: dict[str, Any]) -> str:
        return json.dumps(item, sort_keys=True, default=str)

    older_by_fingerprint = {_fingerprint(item): item for item in older_items}
    newer_by_fingerprint = {_fingerprint(item): item for item in newer_items}

    added = [
        v for k, v in newer_by_fingerprint.items() if k not in older_by_fingerprint
    ]
    removed = [
        v for k, v in older_by_fingerprint.items() if k not in newer_by_fingerprint
    ]

    return {"added": added, "removed": removed, "changed": []}
