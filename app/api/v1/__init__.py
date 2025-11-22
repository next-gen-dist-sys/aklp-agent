"""API v1 package."""

from fastapi import APIRouter

from app.api.v1.endpoints import executor

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(executor.router, prefix="/agent", tags=["executor"])
