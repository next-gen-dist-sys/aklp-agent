"""Usage API endpoints."""

import logging
from typing import Literal

from fastapi import APIRouter, Query, status

from app.core.deps import DBSession
from app.schemas.usage import UsageResponse, UsageStatsData
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/usage",
    response_model=UsageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get API usage statistics",
)
async def get_usage_stats(
    period: Literal["today", "month", "all"] = Query(
        default="all",
        description="Period to aggregate: today, month, or all",
    ),
    db: DBSession = None,  # type: ignore[assignment]
) -> UsageResponse:
    """Get aggregated API usage statistics.

    - **today**: Usage statistics for today (UTC)
    - **month**: Usage statistics for current month (UTC)
    - **all**: All-time usage statistics
    """
    service = UsageService(db)
    stats = await service.get_stats(period=period)

    return UsageResponse(
        success=True,
        data=UsageStatsData(
            total_input_tokens=stats.total_input_tokens,
            total_output_tokens=stats.total_output_tokens,
            total_cached_tokens=stats.total_cached_tokens,
            total_cost_usd=stats.total_cost_usd,
            request_count=stats.request_count,
            period=stats.period,
            period_start=stats.period_start,
            period_end=stats.period_end,
        ),
    )
