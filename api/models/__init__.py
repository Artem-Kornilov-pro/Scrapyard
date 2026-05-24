from api.models.job import (
    ScrapingJobBase,
    ScrapingJobCreate,
    ScrapingJobUpdate,
    ScrapingJobInDB,
    ScrapingJobResponse,
)
from api.models.result import (
    ScrapedResult,
    ScrapedResultResponse,
)

__all__ = [
    "ScrapingJobBase",
    "ScrapingJobCreate",
    "ScrapingJobUpdate",
    "ScrapingJobInDB",
    "ScrapingJobResponse",
    "ScrapedResult",
    "ScrapedResultResponse",
]