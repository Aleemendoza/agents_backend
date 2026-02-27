"""Security dependencies and API key validation."""

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate API key from request header."""

    if not x_api_key or x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
