from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


class CommandRequest(BaseModel):
    """사용자의 자연어 명령을 담는 요청 모델"""

    session_id: UUID | None = Field(None, description="세션 ID (선택 사항)")
    raw_command: str = Field(..., description="사용자의 자연어 명령어")

    model_config = {
        "json_schema_extra": {"example": {"raw_command": "노트 서비스 pod 목록 좀 보여줘"}}
    }


class CommandResponse(BaseModel):
    """실행할 명령어를 담는 응답 모델"""

    session_id: UUID | None = Field(None, description="세션 ID (선택 사항)")
    success: bool = Field(..., description="kubectl 명령어 생성 여부")
    command: str | None = Field(None, description="kubectl 명령어")
    reason: str | None = Field(None, description="명령어 선택 이유")
    title: str | None = Field(None, description="간단한 요약/제목")
    error_message: str | None = Field(None, description="오류 발생 시 오류 메시지")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "command": "kubectl get pods -A",
                "reason": "모든 네임스페이스 파드 목록 조회",
                "title": "List all pods",
                "error_message": None,
            }
        }
    }
