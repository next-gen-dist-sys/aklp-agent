"""API Usage log model for tracking OpenAI API usage."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class APIUsageLog(Base):
    """OpenAI API 사용량 기록 모델."""

    __tablename__ = "api_usage_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    request_log_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)

    def __repr__(self) -> str:
        """String representation of APIUsageLog."""
        return (
            f"<APIUsageLog(id={self.id}, "
            f"model={self.model!r}, "
            f"input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens})>"
        )
