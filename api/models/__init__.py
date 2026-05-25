from api.models.job import (
    ScrapingJobBase,
    ScrapingJobCreate,
    ScrapingJobInDB,
    ScrapingJobResponse,
    ScrapingJobUpdate,
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
