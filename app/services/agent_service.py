from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.agent import AgentRequestLog
from app.models.usage import APIUsageLog
from app.services.command_router import CommandRouter
from app.services.executor import CommandExecutionResult, CommandExecutor
from app.services.pattern_matching_system import PatternMatchingSystem
from app.services.types import GeneratedCommand, UsageInfo


class ExecutorService:
    """자연어 명령 → kubectl 명령 생성 및 (선택적으로) 실행/로그를 담당하는 서비스 레이어"""

    def __init__(
        self,
        db: AsyncSession,
        router: CommandRouter,
        pattern_system: PatternMatchingSystem,
        executor: CommandExecutor | None = None,
    ) -> None:
        """ExecutorService 초기화

        Args:
            db: FastAPI DI로 주입받는 AsyncSession(DBSession)
            router: 자연어 명령 정규화/토크나이즈를 담당하는 라우터
            pattern_system: 패턴 매칭 기반 kubectl 명령 생성기
            executor: 실제 쉘 명령 실행기 (기본값: CommandExecutor)
        """
        self.db = db
        self.router = router
        self.pattern_system = pattern_system
        self.executor = executor or CommandExecutor()

    async def execute_kubectl(
        self,
        kubectl_command: str,
        *,
        context: dict[str, Any] | None = None,
        timeout: int = 30,
        log_to_db: bool = True,
    ) -> CommandExecutionResult:
        """kubectl 명령을 실행하고, 필요하면 DB에 실행 로그를 남김.

        Args:
            kubectl_command: 실행할 kubectl 명령어 (예: 'kubectl get pods -A')
            context: raw_command, session_id 등 부가 정보 (로그에 사용 가능)
            timeout: 명령어 실행 타임아웃 (초)
            log_to_db: True 이면 DB에 실행 결과를 기록

        Returns:
            CommandExecutionResult: 실행 결과 DTO
        """
        result = await self.executor.execute(kubectl_command, timeout=timeout)

        if log_to_db:
            await self._log_execution(
                kubectl_command=kubectl_command,
                result=result,
                context=context or {},
            )

        return result

    async def _log_request(
        self,
        *,
        raw_command: str,
        session_id: UUID | None,
        generated_command: str | None,
        is_success: bool,
        error_message: str | None,
    ) -> UUID:
        """자연어 → kubectl 변환 결과를 요청 로그 테이블에 기록.

        Returns:
            UUID: Created log record ID for correlation with usage log
        """
        log = AgentRequestLog(
            raw_command=raw_command,
            is_success=is_success,
            executed_command=generated_command,
            error_message=error_message,
            session_id=session_id,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log.id

    async def _log_usage(
        self,
        usage: UsageInfo,
        session_id: UUID | None = None,
        request_log_id: UUID | None = None,
    ) -> None:
        """OpenAI API 사용량을 DB에 기록."""
        usage_log = APIUsageLog(
            model=settings.OPENAI_MODEL,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            session_id=session_id,
            request_log_id=request_log_id,
        )
        self.db.add(usage_log)
        await self.db.commit()

    async def _log_execution(
        self,
        kubectl_command: str,
        result: CommandExecutionResult,
        context: dict[str, Any],
    ) -> None:
        """kubectl 실행 결과를 요청 로그 테이블에 간단히 기록."""
        session_id: UUID | None = context.get("session_id")
        raw_command: str = context.get("raw_command", kubectl_command)

        is_success = result.return_code == 0
        error_message: str | None = result.stderr or None

        log = AgentRequestLog(
            raw_command=raw_command,
            is_success=is_success,
            executed_command=kubectl_command,
            error_message=error_message,
            session_id=session_id,
        )
        self.db.add(log)
        await self.db.commit()

    async def execute_command(
        self,
        *,
        raw_command: str,
        session_id: UUID | None,
    ) -> GeneratedCommand:
        """자연어 명령을 받아 kubectl 명령어를 생성하고, 요청 로그를 남긴 뒤 결과 객체를 반환."""
        normalized = self.router.normalize_command(raw_command)

        generated = self.pattern_system.process_command(normalized)

        if isinstance(generated, str):
            await self._log_request(
                raw_command=raw_command,
                session_id=session_id,
                generated_command=None,
                is_success=False,
                error_message=generated,
            )
            raise AppException(message=generated)

        if not generated.command.startswith("kubectl "):
            await self._log_request(
                raw_command=raw_command,
                session_id=session_id,
                generated_command=None,
                is_success=False,
                error_message="kubectl # UNABLE_TO_GENERATE",
            )
            raise AppException(message="kubectl # UNABLE_TO_GENERATE")

        request_log_id = await self._log_request(
            raw_command=raw_command,
            session_id=session_id,
            generated_command=generated.command,
            is_success=True,
            error_message=None,
        )

        # Log API usage if available (only when LLM was called)
        if generated.usage is not None:
            await self._log_usage(
                usage=generated.usage,
                session_id=session_id,
                request_log_id=request_log_id,
            )

        return generated
