from datetime import datetime, UTC
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ResultMetadata(BaseModel):
    """Metadata about a scraping run."""

    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    pages_processed: int = Field(default=1, ge=1)
    status: str = Field(default="success", pattern="^(success|partial|failed)$")
    error_message: Optional[str] = None


class ScrapedResult(BaseModel):
    """Model representing a scraping result stored in MongoDB."""

    job_id: str = Field(..., description="Reference to scraping job")
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items_count: int = Field(default=0, ge=0)
    items: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ResultMetadata = Field(...)


class ScrapedResultResponse(ScrapedResult):
    """Response model for scraping results API."""
    pass