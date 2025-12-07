from __future__ import annotations

from openai import OpenAI
from openai.types.responses import ParsedResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.types import GeneratedCommand, UsageInfo


class KubectlStructuredOutput(BaseModel):
    """Responses API structured output 모델."""

    command: str
    reason: str
    title: str
    model_config = {"extra": "forbid"}


class ComplexCommandProcessor:
    """단순 패턴 매칭에 실패한 자연어 명령어를 LLM을 활용해 kubectl 명령어로 변환하는 프로세서."""

    def __init__(self, client: OpenAI | None = None) -> None:
        api_key = settings.OPENAI_API_KEY
        self.client = client or OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.OPENAI_TIMEOUT
        self.max_output_tokens = 512

    def _build_system_prompt(self) -> str:
        """system 프롬프트 정의"""
        return (
            "You are an expert Kubernetes operator and kubectl CLI generator.\n"
            "The user will give you a request in Korean (sometimes mixed with English).\n"
            "Your job is to convert the request into EXACTLY ONE kubectl command line.\n\n"
            "Requirements:\n"
            "- Output ONLY the kubectl command, nothing else (no explanation, no comments).\n"
            "- Do not wrap the command in quotes or code fences.\n"
            "- Prefer safe, read-only operations when ambiguous (e.g., 'kubectl get ...').\n"
            "- If a namespace is clearly mentioned, add '-n <namespace>'.\n"
            "- If the user mentions '모든 네임스페이스' or '전체 네임스페이스', use '-A'.\n"
            "- If the user refers to an app/service name, use label selectors when appropriate (e.g., '-l app=<name>').\n"
            "- If you truly cannot generate a kubectl command, return exactly: 'kubectl # UNABLE_TO_GENERATE'.\n"
            "- You must always populate the fields: command (kubectl line), reason (brief reasoning), title (concise summary)."
        )

    def _extract_kubectl_command(self, raw: str) -> str:
        """모델 응답에서 실제 kubectl 한 줄 추출."""
        text = raw.strip()

        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("kubectl "):
                return line

        if text.startswith("kubectl "):
            return text

        return text

    def _build_user_input(self, command: str) -> str:
        """사용자 입력 콘텐츠 생성."""
        return f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}"

    def _extract_structured_payload(
        self, response: object
    ) -> tuple[KubectlStructuredOutput | str | None, bool]:
        """
        Responses API 결과에서 Structured Output을 추출.

        반환:
            payload: KubectlStructuredOutput | str | None - 파싱된 모델 또는 거절 메시지
            refused: bool - 거절 여부
        """
        parsed = getattr(response, "output_parsed", None)
        if parsed:
            return parsed, False

        output_items = getattr(response, "output", None) or []
        for item in output_items:
            contents = getattr(item, "content", None) or []
            for content in contents:
                if getattr(content, "type", None) == "refusal":
                    return (
                        f"kubectl # REFUSED: {getattr(content, 'refusal', 'Unknown reason')}",
                        True,
                    )

        return None, False

    def _call_responses(
        self, command: str
    ) -> tuple[KubectlStructuredOutput | None | str, UsageInfo | None]:
        """Responses API 호출을 수행하고 BaseModel로 파싱."""
        usage_info: UsageInfo | None = None

        def _invoke(
            max_tokens: int,
        ) -> tuple[ParsedResponse[KubectlStructuredOutput], UsageInfo | None]:
            resp = self.client.responses.parse(
                model=self.model,
                instructions=self._build_system_prompt(),
                input=self._build_user_input(command),
                max_output_tokens=max_tokens,
                timeout=self.timeout,
                text_format=KubectlStructuredOutput,
            )
            usage: UsageInfo | None = None
            if hasattr(resp, "usage") and resp.usage:
                u = resp.usage
                cached_tokens = 0
                if hasattr(u, "input_tokens_details") and u.input_tokens_details:
                    cached_tokens = getattr(u.input_tokens_details, "cached_tokens", 0) or 0
                usage = UsageInfo(
                    input_tokens=getattr(u, "input_tokens", 0) or 0,
                    output_tokens=getattr(u, "output_tokens", 0) or 0,
                    cached_tokens=cached_tokens,
                )
            return resp, usage

        try:
            response, usage_info = _invoke(self.max_output_tokens)

            if getattr(response, "status", None) == "incomplete":
                details = getattr(response, "incomplete_details", None)
                reason = getattr(details, "reason", "unknown")
                if reason == "max_output_tokens":
                    response, usage_info = _invoke(self.max_output_tokens * 2)
                else:
                    return f"kubectl # INCOMPLETE: {reason}", usage_info

            if getattr(response, "status", None) == "incomplete":
                details = getattr(response, "incomplete_details", None)
                reason = getattr(details, "reason", "unknown")
                return f"kubectl # INCOMPLETE: {reason}", usage_info

            payload, refused = self._extract_structured_payload(response)
            if refused:
                return payload or "kubectl # REFUSED", usage_info

            if isinstance(payload, KubectlStructuredOutput):
                return payload, usage_info

            return "kubectl # UNABLE_TO_GENERATE: empty response", usage_info

        except Exception as e:
            return f"kubectl # LLM_CALL_FAILED: {e}", usage_info

    def process(
        self,
        command: str,
    ) -> GeneratedCommand | str:
        """자연어 명령어를 kubectl 명령어로 변환."""
        structured, usage_info = self._call_responses(command)

        if isinstance(structured, str):
            return structured  # 에러 메시지

        if not isinstance(structured, KubectlStructuredOutput):
            return "kubectl # UNABLE_TO_GENERATE: missing fields command,reason,title"

        kubectl_cmd = self._extract_kubectl_command(structured.command)

        if not kubectl_cmd.startswith("kubectl "):
            return "kubectl # UNABLE_TO_GENERATE"

        return GeneratedCommand(
            command=kubectl_cmd,
            reason=structured.reason,
            title=structured.title,
            usage=usage_info,
        )
