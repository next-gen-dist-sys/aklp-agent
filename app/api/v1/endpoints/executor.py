import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_executor_service
from app.core.exceptions import AppException
from app.schemas.agent import CommandRequest, CommandResponse
from app.services.agent_service import ExecutorService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/execute",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute natural language command",
)
async def execute_command(
    command_request: CommandRequest,
    executor_service: ExecutorService = Depends(get_executor_service),
) -> CommandResponse:
    try:
        generated_command = await executor_service.execute_command(
            raw_command=command_request.raw_command,
            session_id=command_request.session_id,
        )

        return CommandResponse(
            session_id=command_request.session_id,
            success=True,
            command=generated_command.command,
            reason=generated_command.reason,
            title=generated_command.title,
            error_message=None,
        )

    except AppException as e:
        # 도메인 에러: 200 + success=False
        return CommandResponse(
            session_id=command_request.session_id,
            success=False,
            command=None,
            reason=None,
            title=None,
            error_message=e.message,
        )

    except Exception as e:
        logger.exception("Unexpected error in execute_command", extra={"request_id": "N/A"})

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {e}",
        ) from e
