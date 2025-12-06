"""Usage schemas for API responses."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class UsageStatsData(BaseModel):
    """Usage statistics data."""

    total_input_tokens: int = Field(..., description="Total input tokens used")
    total_output_tokens: int = Field(..., description="Total output tokens generated")
    total_cached_tokens: int = Field(..., description="Total cached input tokens")
    total_cost_usd: Decimal = Field(..., description="Total cost in USD")
    request_count: int = Field(..., description="Number of API requests")
    period: str = Field(..., description="Period type: today, month, or all")
    period_start: datetime | None = Field(None, description="Start of the period (UTC)")
    period_end: datetime | None = Field(None, description="End of the period (UTC)")


class UsageResponse(BaseModel):
    """Usage statistics response."""

    success: bool = Field(default=True, description="Whether the request was successful")
    data: UsageStatsData = Field(..., description="Usage statistics data")
