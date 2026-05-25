from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from croniter import croniter # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator


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
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("selectors")
    @classmethod
    def validate_selectors(cls, v: dict) -> dict:
        """Validate selectors structure."""
        if "items" not in v:
            raise ValueError("selectors must contain 'items' key")
        if "fields" not in v:
            raise ValueError("selectors must contain 'fields' key")
        if not isinstance(v["fields"], dict) or len(v["fields"]) == 0:
            raise ValueError("selectors.fields must be a non-empty dict")
        return v


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
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


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
