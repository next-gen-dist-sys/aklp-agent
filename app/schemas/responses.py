"""Common response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    request_id: str = Field(..., description="Request ID for tracing")


class SuccessResponse(BaseResponse, Generic[T]):
    """Success response model."""

    success: bool = Field(default=True, description="Always True for success responses")
    data: T = Field(..., description="Response data")


class ErrorResponse(BaseResponse):
    """Error response model."""

    success: bool = Field(default=False, description="Always False for error responses")
    error_code: str = Field(..., description="Error code")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    database: str = Field(..., description="Database connection status")
