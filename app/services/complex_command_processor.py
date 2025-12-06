from __future__ import annotations

import json

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.types import GeneratedCommand, UsageInfo


class KubectlStructuredOutput(BaseModel):
    """Responses API structured output 모델."""

    command: str
    reason: str
    title: str


class ComplexCommandProcessor:
    """단순 패턴 매칭에 실패한 자연어 명령어를 LLM을 활용해 kubectl 명령어로 변환하는 프로세서."""

    def __init__(self, client: OpenAI | None = None) -> None:
        api_key = settings.OPENAI_API_KEY
        self.client = client or OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.OPENAI_TIMEOUT

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

    def _build_input_messages(self, command: str) -> list[dict[str, str]]:
        """Responses API input 메시지 생성."""
        return [
            {
                "role": "developer",
                "content": self._build_system_prompt(),
            },
            {
                "role": "user",
                "content": f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}",
            },
        ]

    def _call_responses(self, command: str) -> tuple[KubectlStructuredOutput | None | str, UsageInfo | None]:
        """Responses API 호출을 수행하고 BaseModel로 파싱."""
        messages = self._build_input_messages(command)
        usage_info: UsageInfo | None = None

        # JSON Schema for structured output
        json_schema = {
            "type": "json_schema",
            "name": "kubectl_command",
            "schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The kubectl command line"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reasoning for the command"
                    },
                    "title": {
                        "type": "string",
                        "description": "Concise summary title"
                    }
                },
                "required": ["command", "reason", "title"],
                "additionalProperties": False
            },
            "strict": True
        }

        try:
            response = self.client.responses.create(
                model=self.model,
                input=messages,
                max_output_tokens=256,
                timeout=self.timeout,
                text={"format": json_schema},
            )

            # Extract usage information
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                cached_tokens = 0
                if hasattr(usage, 'input_tokens_details') and usage.input_tokens_details:
                    cached_tokens = getattr(usage.input_tokens_details, 'cached_tokens', 0) or 0
                usage_info = UsageInfo(
                    input_tokens=getattr(usage, 'input_tokens', 0) or 0,
                    output_tokens=getattr(usage, 'output_tokens', 0) or 0,
                    cached_tokens=cached_tokens,
                )

            # Check for refusal
            if response.output and len(response.output) > 0:
                first_output = response.output[0]
                if hasattr(first_output, 'content') and first_output.content:
                    content = first_output.content[0]
                    if hasattr(content, 'type') and content.type == "refusal":
                        return f"kubectl # REFUSED: {getattr(content, 'refusal', 'Unknown reason')}", usage_info

            # Get output text and parse JSON
            output_text = getattr(response, 'output_text', None)
            if not output_text and response.output:
                # Fallback: try to get text from output structure
                first_output = response.output[0]
                if hasattr(first_output, 'content') and first_output.content:
                    content = first_output.content[0]
                    if hasattr(content, 'text'):
                        output_text = content.text

            if output_text:
                try:
                    data = json.loads(output_text)
                    return KubectlStructuredOutput(**data), usage_info
                except (json.JSONDecodeError, TypeError) as e:
                    return f"kubectl # JSON_PARSE_FAILED: {e}", usage_info

            return None, usage_info

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
