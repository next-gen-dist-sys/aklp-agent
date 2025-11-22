"""Agent model for database."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class AgentRequestLog(Base):
    """
    사용자의 자연어 명령어 요청 및 시스템의 처리 결과를 기록하는 모델.
    CommandRequest와 CommandResponse의 핵심 필드를 저장합니다.
    """

    __tablename__ = "agent_request_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    raw_command: Mapped[str] = mapped_column(String(512), nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_at: Mapped[datetime] = mapped_column(nullable=False, default=func.now())
    executed_command: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    session_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)

    def __repr__(self) -> str:
        """String representation of AgentRequestLog."""
        return (
            f"<AgentRequestLog(id={self.id}, "
            f"raw_command={self.raw_command!r}, "
            f"is_success={self.is_success})>"
        )
