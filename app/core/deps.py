"""Dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.agent_service import ExecutorService
from app.services.command_router import CommandRouter
from app.services.complex_command_processor import ComplexCommandProcessor
from app.services.executor import CommandExecutor
from app.services.pattern_matching_system import PatternMatchingSystem

# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Type alias for database dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_executor_service(
    db: DBSession,
) -> ExecutorService:
    router = CommandRouter()
    complex_processor = ComplexCommandProcessor()
    pattern_system = PatternMatchingSystem(complex_processor)
    executor = CommandExecutor()

    return ExecutorService(
        db=db,
        executor=executor,
        router=router,
        pattern_system=pattern_system,
    )
