"""Shared response helpers."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """API error envelope for non-execution failures."""

    detail: str
