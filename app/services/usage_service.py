"""Usage service for tracking and reporting OpenAI API usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import APIUsageLog

# 가격 정보 (per 1M tokens)
PRICING: dict[str, dict[str, Decimal]] = {
    "gpt-5-mini": {
        "input": Decimal("0.25"),
        "cached": Decimal("0.025"),
        "output": Decimal("2.00"),
    },
    "gpt-5": {
        "input": Decimal("0.25"),
        "cached": Decimal("0.025"),
        "output": Decimal("2.00"),
    },
}

DEFAULT_PRICING = PRICING["gpt-5-mini"]


@dataclass
class UsageStats:
    """Usage statistics data class."""

    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_cost_usd: Decimal
    request_count: int
    period: str
    period_start: datetime | None
    period_end: datetime | None


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    model: str,
) -> Decimal:
    """Calculate cost based on token usage.

    Args:
        input_tokens: Total input tokens (includes cached)
        output_tokens: Output tokens
        cached_tokens: Cached input tokens (subset of input_tokens)
        model: Model name for pricing lookup

    Returns:
        Total cost in USD
    """
    pricing = PRICING.get(model, DEFAULT_PRICING)

    # cached_tokens는 input_tokens에 포함되어 있으므로 분리 계산
    regular_input = input_tokens - cached_tokens

    input_cost = (Decimal(regular_input) / 1_000_000) * pricing["input"]
    cached_cost = (Decimal(cached_tokens) / 1_000_000) * pricing["cached"]
    output_cost = (Decimal(output_tokens) / 1_000_000) * pricing["output"]

    return input_cost + cached_cost + output_cost


class UsageService:
    """Service for logging and querying API usage."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize usage service.

        Args:
            db: Async database session
        """
        self.db = db

    async def log_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        session_id: UUID | None = None,
        request_log_id: UUID | None = None,
    ) -> APIUsageLog:
        """Log API usage to database.

        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens
            session_id: Optional session ID
            request_log_id: Optional request log ID for correlation

        Returns:
            Created APIUsageLog record
        """
        log = APIUsageLog(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            session_id=session_id,
            request_log_id=request_log_id,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_stats(self, period: str = "all") -> UsageStats:
        """Get aggregated usage statistics.

        Args:
            period: One of "today", "month", or "all"

        Returns:
            UsageStats with aggregated data
        """
        now = datetime.now(timezone.utc)
        period_start: datetime | None = None
        period_end: datetime | None = now

        if period == "today":
            # Start of today (UTC)
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            # Start of current month (UTC)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # "all" - no date filter
            period_start = None
            period_end = None

        # Build query
        query = select(
            func.coalesce(func.sum(APIUsageLog.input_tokens), 0).label("total_input"),
            func.coalesce(func.sum(APIUsageLog.output_tokens), 0).label("total_output"),
            func.coalesce(func.sum(APIUsageLog.cached_tokens), 0).label("total_cached"),
            func.count(APIUsageLog.id).label("request_count"),
        )

        if period_start is not None:
            query = query.where(APIUsageLog.created_at >= period_start)

        result = await self.db.execute(query)
        row = result.one()

        total_input = int(row.total_input)
        total_output = int(row.total_output)
        total_cached = int(row.total_cached)
        request_count = int(row.request_count)

        # Calculate cost (using default model for aggregated stats)
        total_cost = calculate_cost(
            input_tokens=total_input,
            output_tokens=total_output,
            cached_tokens=total_cached,
            model="gpt-5-mini",
        )

        return UsageStats(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cached_tokens=total_cached,
            total_cost_usd=total_cost,
            request_count=request_count,
            period=period,
            period_start=period_start,
            period_end=period_end,
        )
