from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from croniter import croniter  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

from api.models.validators import validate_selectors_structure, validate_url_format


class ScrapingJobBase(BaseModel):
    """Base model for scraping job configuration."""

    name: str = Field(..., min_length=1, max_length=255, description="Job name")
    url: str = Field(..., description="Target URL to scrape")
    method: str = Field(default="GET", pattern="^(GET|POST)$")
    selectors: dict = Field(..., description="CSS selectors configuration")
    schedule: str = Field(
        default="0 */6 * * *",
        description="Cron expression for scheduling",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for grouping")
    settings: dict = Field(
        default_factory=lambda: {
            "wait_until": "networkidle",
            "timeout": 30,
            "pagination": {"type": None, "max_pages": 1},
        },
        description="Scraping settings",
    )
    notify_webhook: Optional[str] = Field(
        default=None,
        description="Webhook URL to POST to when the job hits 5 "
        "consecutive failures and is marked as 'error'",
    )
    diff_key: Optional[str] = Field(
        default=None,
        description="Field name used to match items across runs when "
        "diffing two results (e.g. 'title'). Without it, diffs fall "
        "back to comparing whole items, so any field change shows up "
        "as a remove+add instead of a per-field change.",
    )

    @field_validator("schedule")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression."""
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        return validate_url_format(v)

    @field_validator("selectors")
    @classmethod
    def validate_selectors(cls, v: dict) -> dict:
        """Validate selectors structure."""
        return validate_selectors_structure(v)

    @field_validator("notify_webhook")
    @classmethod
    def validate_notify_webhook(cls, v: Optional[str]) -> Optional[str]:
        """Validate webhook URL format if provided."""
        if v is None:
            return v
        return validate_url_format(v)


class ScrapingJobCreate(ScrapingJobBase):
    """Model for creating a new scraping job."""
    pass


class ScrapingJobUpdate(BaseModel):
    """Model for updating an existing scraping job."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(GET|POST)$")
    selectors: Optional[dict] = None
    schedule: Optional[str] = None
    tags: Optional[list[str]] = None
    settings: Optional[dict] = None
    notify_webhook: Optional[str] = None
    diff_key: Optional[str] = None

    @field_validator("schedule")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression if provided."""
        if v is not None and not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is None:
            return v
        return validate_url_format(v)

    @field_validator("notify_webhook")
    @classmethod
    def validate_notify_webhook(cls, v: Optional[str]) -> Optional[str]:
        """Validate webhook URL format if provided."""
        if v is None:
            return v
        return validate_url_format(v)


class ScrapingJobInDB(ScrapingJobBase):
    """Model representing a scraping job stored in MongoDB."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = Field(default="active", pattern="^(active|paused|error)$")
    consecutive_failures: int = Field(default=0, ge=0)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScrapingJobResponse(ScrapingJobInDB):
    """Response model for scraping job API."""
    pass


class DryRunRequest(BaseModel):
    """Request to test selectors against a live page without saving a job."""

    url: str = Field(..., description="Target URL to scrape")
    selectors: dict = Field(..., description="CSS selectors configuration")
    settings: dict = Field(
        default_factory=dict, description="Scraping settings (e.g. pagination)"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_url_format(v)

    @field_validator("selectors")
    @classmethod
    def validate_selectors(cls, v: dict) -> dict:
        return validate_selectors_structure(v)


class DryRunResult(BaseModel):
    """Result of a dry run."""

    success: bool
    items_count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    truncated: bool = False
    error: Optional[str] = None
