from __future__ import annotations

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.types import GeneratedCommand


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

    def _build_input_messages(self, command: str) -> list[dict[str, object]]:
        """Responses API input 메시지 생성."""
        system_prompt = self._build_system_prompt()
        return [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"다음 요청을 하나의 kubectl 명령어로 변환해 주세요.\n요청: {command}"
                        ),
                    }
                ],
            },
        ]

    def _call_responses(self, command: str) -> KubectlStructuredOutput | None | str | BaseModel:
        """Responses API 호출을 수행하고 BaseModel로 파싱."""
        messages = self._build_input_messages(command)

        try:
            parsed = self.client.responses.parse(  # type: ignore[call-arg]
                model=self.model,
                input=messages,  # type: ignore[arg-type]
                max_output_tokens=128,
                timeout=self.timeout,
                response_format=KubectlStructuredOutput,
            )
            first = None
            if parsed.output_parsed:
                first = parsed.output_parsed[0]
            elif parsed.output and parsed.output[0].parsed:  # type: ignore[union-attr]
                first = parsed.output[0].parsed  # type: ignore[union-attr]
        except TypeError:
            # SDK가 BaseModel response_format을 지원하지 않는 경우 json_schema로 재시도
            fallback_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "KubectlCommand",
                    "schema": KubectlStructuredOutput.model_json_schema(),
                    "strict": True,
                },
            }
            parsed = self.client.responses.create(  # type: ignore[call-overload]
                model=self.model,
                input=messages,
                max_output_tokens=128,
                timeout=self.timeout,
                response_format=fallback_schema,
            )
            first = parsed.output[0].parsed if parsed.output else None
        except Exception as e:
            return f"kubectl # LLM_CALL_FAILED: {e}"

        if isinstance(first, BaseModel):
            return first
        if isinstance(first, dict):
            try:
                return KubectlStructuredOutput(**first)
            except Exception:
                return None
        return None

    def process(
        self,
        command: str,
    ) -> GeneratedCommand | str:
        """자연어 명령어를 kubectl 명령어로 변환."""
        structured = self._call_responses(command)

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
        )
