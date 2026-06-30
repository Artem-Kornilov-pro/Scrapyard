from fastapi import Header, HTTPException, status

from api.core.config import settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Require a matching X-API-Key header on protected routes.

    Auth is disabled when API_KEY is unset, which keeps local development
    and the test suite working without extra setup. Set API_KEY in
    production to require it on every request.
    """
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
